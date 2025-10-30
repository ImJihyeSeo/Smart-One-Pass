# 얼굴 인식 기반 출입 관리 키오스크 애플리케이션

## 프로그램 구조
---
```
kiosk_gate/
├── main.py                		           # 메인 애플리케이션 (MainWindow)
├── ui_style.py               		       # 설정 상수 관리 / 스타일 정의 파일
├── cv_tools.py             		         # 얼굴 감지/인식 관련 툴 함수
├── ui_pages/
│   ├── base_page.py        	           # 공통 헤더 및 컨텐츠 영역을 제공하는 페이지
│   ├── common_header.py    	           # 로고, 텍스트, X 버튼을 포함한 헤더 위젯
│   ├── idle_page.py        	           # 시작/대기 화면
│   ├── processing_page.py 	             # 얼굴 인식 진행 페이지
│   ├── result_page.py      	           # 인증 + 등록 결과 표시 페이지
│   ├── enrollment_input_page.py    	 	 # 등록 전 학생 정보 (이름/학번) 입력 받는 페이지
│   ├── enrollment_start_page.py    		 # 촬영 유의사항 안내 페이지
│   ├── enrollment_recording_page.py     # 3단계 촬영 진행 페이지
├── backend/
│   ├── database.py                     # DB 관련 함수
│   ├── main.py                         # 나중에 변경할 예정
│   ├── requirement.txt                 # 필요한 기능 설치
│   ├── assets/
│   │   ├── OnePassDB.db                # DB 테이블
│   │   ├── init.sql                    # SQL 테이블
│   ├── back/
│   │   ├── api/
│   │   │   ├── access_api.py           # 출입 관련 API
│   │   │   ├── seat_api.py             # 좌석 예약 API
│   │   │   ├── user_api.py             # 학생 정보 관련 API
│   │   ├── services/
│   │   │   ├── core_service.py         # API 핵심 내부 함수
│   │   ├── utils/
│   │   │   ├── helper_function.py      # API 공통 내부 함수
└── resources/             	 	           # 이미지, 아이콘 파일
```

## 환경 설정
---
Python 3.9 이상 환경에서 프로젝트를 실행해야 한다. 필요한 라이브러리를 설치한다.
```
pip install pyside6 opencv-python numpy
```

## 어플리케이션 실행
---
프로젝트 루트 디렉토리에서 main.py를 실행한다.
```
python main.py
```
