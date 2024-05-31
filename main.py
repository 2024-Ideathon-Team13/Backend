from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

import os
from logger import logger
import sys
import dotenv
import boto3


app = FastAPI()
router = APIRouter(prefix="/api/v1")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# origins = [
#     "http://127.0.0.1:5173",  # 또는 "http://localhost:5173"
# ]


# try:
#     models.Base.metadata.create_all(bind=engine)
#     logger.info("테이블 생성 완료")
#     insert_initial_data()  # 테이블 생성 후 초기 데이터 삽입
#     logger.info("초기 데이터 삽입 완료")
# except Exception as e:
#     logger.error("테이블 생성 실패")
#     logger.info(e)
#     sys.exit(1)


@app.get("/")
def hello():
    return {"message": "메인페이지입니다"}
