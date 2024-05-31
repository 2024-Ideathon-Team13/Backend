from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from pydantic import BaseModel
import pytz
import os
from dotenv import load_dotenv
from logger import logger
import sys
import openai
import boto3


app = FastAPI()

# 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

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
def generate_image_logic(content):
    try:
        prompt_keyword = """Design: a detailed digital illustration drawn with bright colors and clean lines. Please make the following images according to the previous requirements: """

        response = openai.Image.create(
            model="dall-e-3",
            size="1024x1024",
            quality="standard",
            prompt="""
                When generating an image, be sure to observe the following conditions: Do not add text to the image. 
                I want an illustration image, not contain text in the image.
                """ + prompt_keyword + content,
            n=1
        )
        return response['data'][0]['url']
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 요청 모델 정의
class ImageRequest(BaseModel):
    content: str

@app.post("/generate-image")
async def generate_image(request: ImageRequest):
    image_url = generate_image_logic(request.content)
    return {"image_url": image_url}


# @app.get("/")
# def read_root():
#     return {"message": "Hello, this is the DALL-E image generator API"}

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

# 초기 데이터 삽입
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

@app.get("/")
def hello():
    return {"message": "메인페이지입니다"}
