from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends
from datetime import datetime
from pydantic import BaseModel
import pytz
import os
from dotenv import load_dotenv
from logger import logger
import sys
import boto3
from openai import OpenAI
from PIL import Image
from io import BytesIO
from fastapi import UploadFile
from fastapi.responses import FileResponse

app = FastAPI()

# 환경 변수 로드
load_dotenv()

client = OpenAI(api_key = os.getenv("OPENAI_API_KEY") )
# S3 클라이언트 설정
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv("CREDENTIALS_ACCESS_KEY"),
    aws_secret_access_key=os.getenv("CREDENTIALS_SECRET_KEY"),
    region_name=os.getenv("CREDENTIALS_AWS_REGION")
)

@app.get("/test-s3")
async def test_s3_connection():
    try:
        response = s3_client.list_buckets()
        buckets = [bucket['Name'] for bucket in response['Buckets']]
        return {"buckets": buckets}
    except Exception as e:
        logger.error(f"Failed to connect to S3: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to S3")

# 이미지 생성 로직
# def generate_image_logic(content: str):
#     try:
#         response = client.images.generate(
#             model="dall-e-3",
#             prompt="A sunlit indoor lounge area with a pool with clear water"
#             "and another pool with translucent pastel pink water, next"
#             " to a big window, digital art",
#             size="1024x1024",
#             quality="standard",
#             n=1,
#         )
#         return response.data[0].url
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# 이미지 생성 로직
def generate_image_logic(image: UploadFile):
    try:
        # 업로드된 이미지를 메모리에 로드
        image_bytes = image.file.read()
        image = Image.open(BytesIO(image_bytes))

        # 이미지를 처리하고, 이를 기반으로 텍스트 프롬프트 생성
        # 여기서는 간단히 프롬프트를 하드코딩하였습니다. 실제 구현에서는 이미지 특징을 분석하여 프롬프트 생성 필요
        prompt = "An animated version of various iconic Korean scenes, including Gyeongbokgung Palace, Han River at night, Dol Hareubang statue by the sea in Jeju Island, a horse in a grassy field with a stone wall in Jeju Island, Hallasan mountain and its crater lake on Jeju Island, a traditional Korean gate in a city setting, a riverside path lined with cherry blossom trees, and a large airport with multiple airplanes. Each scene is vibrant, colorful, and depicted in a whimsical, cartoonish manner with exaggerated features and bright colors, suitable for an animated movie or children's storybook."

        response = openai.Image.create(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )

        return response['data'][0]['url']
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 요청 모델 정의
class ImageRequest(BaseModel):
    content: str

@app.post("/generate-image")
async def generate_image(request: ImageRequest):
    image_url = generate_image_logic(request.content)
    return {"image_url": image_url}

@app.get("/")
def read_root():
    return {"message": "Hello, this is the DALL-E image generator API"}

# 한국 시간대 설정
kst = pytz.timezone('Asia/Seoul')

# 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("데이터베이스 URL이 설정되지 않았습니다.")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 모델 정의
class Photo(Base):
    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String(500), nullable=False)
    dalle_url = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(tz=kst))

# 데이터베이스 초기화
def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("테이블 생성 완료")

# 데이터베이스 의존성 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/photos/original")
def read_original_photos(db: Session = Depends(get_db)):
    return [photo.original_url for photo in db.query(Photo).all()]

@app.get("/photos/dalle")
def read_dalle_photos(db: Session = Depends(get_db)):
    return [photo.dalle_url for photo in db.query(Photo).all()]

# GET, id로 원본 사진과 달리 사진 조회
@app.get("/photos/{photo_id}")
def read_photos(photo_id: int, db: Session = Depends(get_db)):
    photo = db.query(Photo).filter(Photo.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다")
    return {"original_photo": photo.original_url, "dalle_photo": photo.dalle_url}

def insert_initial_data():
    db: Session = SessionLocal()
    try:
        photos = [
            Photo(
                original_url="https://example.com/original.jpg",
                dalle_url="https://example.com/dalle.jpg",
                created_at=datetime(2021, 1, 1, 0, 0, 0, tzinfo=kst)
            )
        ]
        
        db.add_all(photos)
        db.commit()
        logger.info("초기 데이터 삽입 완료")
    except Exception as e:
        db.rollback()
        logger.error(f"초기 데이터 삽입 실패: {e}")
    finally:
        db.close()

# DB 초기화 및 초기 데이터 삽입
if __name__ == "__main__":
    try:
        init_db()
        insert_initial_data()
    except Exception as e:
        logger.error(f"초기화 실패: {e}")
        sys.exit(1)

try:
    Base.metadata.create_all(bind=engine)
    logger.info("테이블 생성 완료")
    insert_initial_data()  # 테이블 생성 후 초기 데이터 삽입
    logger.info("초기 데이터 삽입 완료")
except Exception as e:
    logger.error("테이블 생성 실패")
    logger.info(e)
    sys.exit(1)

# @app.get("/")
# def hello():
#     return {"message": "메인페이지입니다"}
