from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv
from logger import logger
import sys

# 환경 변수 로드
load_dotenv()

# 한국 시간대 설정
kst = pytz.timezone('Asia/Seoul')

# 데이터베이스 설정
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("데이터베이스 URL이 설정되지 않았습니다.")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI()

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

# 초기 데이터 삽입k
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
