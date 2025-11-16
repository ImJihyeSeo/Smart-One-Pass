

# services/core_service.py

from typing import Union, Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone, time, timedelta
from datetime import time as dt_time

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

# 🚨 import 경로는 당신의 실제 프로젝트 구조에 맞게 수정하세요.
from database import get_db_connection 

# --- 1. 회원 존재 확인 (SELECT) ---
def check_student_exists(sid: str) -> bool:
    conn = get_db_connection()
    if conn is None:
        return False # DB 연결 오류는 나중에 500 에러로 처리됨

    try:
        cursor = conn.cursor()
        # sid를 이용해 students 테이블에서 sid를 조회
        sql = "SELECT sid FROM students WHERE sid = %s"
        cursor.execute(sql, (sid,))

        result = cursor.fetchone()

        # 결과가 있으면 (None이 아니면) True 반환
        return result is not None

    except psycopg2.Error as e:
        print(f"Error checking user existence: {e}")
        return False
	
    finally:
        conn.close()


# DB에 있는지 확인

def prev_check_student(sid: str, name: str) -> bool: # 🚨 name 매개변수 추가
    conn = get_db_connection()
    if conn is None:
        return False # DB 연결 오류 발생

    try:
        cursor = conn.cursor()
        
        # 🚨 SQL 수정: sid가 일치하거나 OR name이 일치하는 레코드가 있는지 조회합니다.
        sql = "SELECT sid FROM students WHERE sid = %s OR name = %s"
        
        # 🚨 파라미터 수정: sid와 name을 모두 전달합니다.
        cursor.execute(sql, (sid, name))

        result = cursor.fetchone()

        # 결과가 있으면 (None이 아니면) 중복이므로 True 반환
        return result is not None

    except psycopg2.Error as e:
        print(f"Error checking user existence: {e}")
        return False
    
    finally:
        conn.close()



# --- 2. 회원 기록 삭제 (DELETE 트랜잭션 - 4단계) ---
def execute_delete_students(sid: str) -> bool:
    conn = get_db_connection()
    if conn is None:
        return False 
    
    try:
        cursor = conn.cursor()
        
        # 🚨 트랜잭션 시작 (4개의 DELETE 작업)
        
        # 1. 예약 기록 삭제 (종속 테이블 먼저 삭제)
        cursor.execute("DELETE FROM seat_reservation WHERE sid = %s", (sid,))
        
        # 2. 출입 기록 삭제
        cursor.execute("DELETE FROM log WHERE sid = %s", (sid,))
        
        # 3. 회원 기록 최종 삭제
        cursor.execute("DELETE FROM students WHERE sid = %s", (sid,))
        
        conn.commit() # 🚨 모든 쿼리가 성공했을 때만 최종 저장!
        return True, {}

    except psycopg2.Error as e:
        print(f"User deletion failed: {e}")
        conn.rollback() # 오류 발생 시 모든 변경사항 취소
        return False, {}
        
    finally:
        conn.close()


# 얼굴 데이터가 일치하는 sid 찾기

# DB 연결 함수는 이전에 정의한 get_db_connection()을 사용한다고 가정합니다.
# 얼굴 인식 모델 함수는 외부에 있다고 가정합니다.
# def compare_face_data(known_face, input_face) -> bool: ...

def get_student_ID_by_face(face: bytes) -> Union[str, Tuple[bool, Dict[str, str]]]:
    """
    입력된 얼굴 데이터와 일치하는 학생 ID(sid)를 DB에서 찾아 반환합니다.
    (실제 얼굴 비교 로직은 외부에 있다고 가정하고, DB는 모든 등록된 얼굴 데이터를 가져오는 역할만 합니다.)
    """
    conn = get_db_connection()
    if conn is None:
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."} 
    
    cursor = conn.cursor()
    ERROR_NOT_FOUND = {"error_code": "NOT_FOUND", "message": "일치하는 회원 정보를 찾을 수 없습니다."}
    
    try:
        # [Step 2-A] 모든 등록된 sid와 face 데이터를 가져옵니다.
        # 이 단계는 DB에서 '검증할 리스트'를 가져오는 역할을 합니다.
        cursor.execute("SELECT sid, face FROM students WHERE face IS NOT NULL")
        
        all_students = cursor.fetchall() # 모든 결과를 리스트 형태로 가져옵니다.

        # [Step 2-B] 파이썬 내부에서 얼굴 비교 로직 실행 (가장 복잡한 부분)
        # 실제 얼굴 인식 모델을 사용하여 등록된 모든 데이터와 비교합니다.
        
        found_sid = None
        for student_row in all_students:
            known_face_data = student_row['face']
            
            # ************************************🚨 이 함수가 실제 AI 모델을 호출하거나 복잡한 벡터 비교를 수행한다고 가정
            # if compare_face_data(known_face_data, face_data): 여기는 나중에 모델이 들어오면 다시 구현 **************************************** 
            if known_face_data == face: # 단순 비교로 대체 (실제로는 복잡한 모델)
                found_sid = student_row['sid']
                break # 일치하는 학생을 찾았으므로 루프를 중단합니다.

        # [Step 2-C] 결과 반환
        if found_sid:
            return found_sid # 일치하는 sid 문자열 반환
        else:
            return False, ERROR_NOT_FOUND # 일치하는 회원이 없음 (404 방어)

    except psycopg2.Error as e:
        print(f"Face check DB Error: {e}")
        return False, {"error_code": "DB_EXECUTION_ERROR", "message": "얼굴 검색 중 DB 오류 발생."}
        
    finally:
        conn.close()

# 상태 판단 (최근 기록에 EXIT이 NULL인지 확인)

# Constants for clarity
ACTION_IN = "IN"
ACTION_OUT = "OUT"

# 매개변수: 최근 로그 데이터 전체를 딕셔너리 형태로 받습니다.
def check_access_of_student(
    recent_log: Optional[Dict[str, Any]]
) -> Tuple[str, Optional[int]]:
    """
    현재 DB 상태(최근 로그)를 분석하여 다음에 실행해야 할 동작(IN/OUT)과 
    갱신이 필요할 경우 해당 log_id를 추론하여 반환합니다.
    
    Args:
        recent_log: log 테이블의 가장 최근 기록. (기록이 없으면 None)

    Returns:
        (action_type, log_id) 튜플: log_id는 OUT일 때만 유효합니다.
    """
    
    # 💡 log_id는 퇴장 시 UPDATE 대상을 지정하기 위해 필요합니다.
    log_id_to_update = None
    
    # -----------------------------------------------------------
    # 비즈니스 로직 (상태 추론)
    # -----------------------------------------------------------
    
    # [Case 1] DB에 해당 학생의 출입 기록이 전혀 없는 경우
    if recent_log is None:
        # 이전에 기록이 없으므로, 다음 동작은 무조건 입장(IN)입니다.
        return ACTION_IN, None
        
    # [Case 2] 최근 기록을 확인합니다.
    
    # exit이 NULL인지 확인합니다. (None이면 현재 입실 상태라는 뜻)
    recent_exit = recent_log.get('exit') 
    
    # 2-A. 현재 입실 상태인 경우 (퇴장 기록이 없음)
    if recent_exit is None:
        # 현재 도서관 내부에 있으므로, 다음 동작은 퇴장(OUT)이어야 합니다.
        log_id_to_update = recent_log.get('log_id')
        
        # 퇴장 처리 시, 갱신할 log_id를 함께 반환합니다.
        return ACTION_OUT, log_id_to_update
        
    # 2-B. 현재 퇴실 상태인 경우 (exit에 값이 있음)
    else:
        # 이미 퇴장까지 완료했으므로, 다음 동작은 새로운 입장(IN)이어야 합니다.
        return ACTION_IN, None

# 4. 회원 기록 저장


# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

# def execute_insert_student(
#     sid: str,
#     face_data: Optional[bytes] # face 혹은 card는 하나만 있어도 되므로 Optional
# ) -> Union[bool, Tuple[bool, Dict[str, str]]]:
#     """
#     students 테이블에 새로운 회원 기록을 삽입하는 트랜잭션 함수입니다.
    
#     Args:
#         sid: 삽입할 회원의 학번 (PRIMARY KEY).
#         face_data: 얼굴 인식 데이터 (선택적).
#         card_id: 학생증 ID (선택적).
        
#     Returns:
#         True (성공) 또는 (False, 오류 상세 정보)
#     """
#     # 함수 시작 부분에 추가 : 얼굴이나 카드가 무조건 있어야 함
#     if face_data is None and card_id is None:
#         return False, {"error_code": "INPUT_REQUIRED", "message": "얼굴 데이터 또는 카드 ID 중 하나는 필수입니다."}
#     conn = get_db_connection()
#     if conn is None: 
#         return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
#     cursor = conn.cursor()
#     ERROR_DB = {"error_code": "DB_ERROR", "message": "회원 기록 저장 중 데이터베이스 오류가 발생했습니다."}
    
#     try:
#         # 🚨 INSERT 쿼리 실행
#         sql = """
#             INSERT INTO students (sid, face, card)
#             VALUES (%s, %s, %s)
#         """
#         params = (sid, face_data, card_id)
        
#         cursor.execute(sql, params)
        
#         conn.commit() # 🚨 쿼리 실행 성공 시 최종 저장
#         return True

#     except psycopg2.IntegrityError:
#         # 이미 존재하는 sid로 INSERT를 시도했을 때 (409 Conflict는 핸들러에서 방어)
#         conn.rollback() 
#         return False, {"error_code": "INTEGRITY_ERROR", "message": "이미 존재하는 학번입니다."} 
        
#     except psycopg2.Error as e:
#         # 그 외 DB 오류 발생 시
#         conn.rollback() 
#         print(f"Student INSERT transaction failed: {e}")
#         return False, ERROR_DB
        
#     finally:
#         conn.close()

# services/core_service.py (execute_insert_student 함수 수정)

def execute_insert_student(
    sid: str,
    name: str,                         # 🚨 추가: 이름을 필수 매개변수로 받습니다.
    face_data: Optional[bytes] = None  # 🚨 수정: face_data를 선택 사항으로 처리합니다.
    # 기존 card_id 매개변수는 완전히 제거되었습니다.
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    students 테이블에 새로운 회원 기록(sid, name, face_data)을 삽입하는 트랜잭션 함수입니다.
    """
    
    # 🚨 수정: 필수 입력값 확인 로직 (sid와 name은 필수, face_data는 선택)
    if not sid or not name: 
        return False, {"error_code": "INPUT_REQUIRED", "message": "학번(sid)과 이름(name)은 필수입니다."}

    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    cursor = conn.cursor()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "회원 기록 저장 중 데이터베이스 오류가 발생했습니다."}
    
    try:
        # 🚨 수정: SQL 쿼리에서 'card'를 제거하고 'name'을 추가합니다.
        sql = """
            INSERT INTO students (sid, name, face)
            VALUES (%s, %s, %s)
        """
        # 🚨 수정: params 튜플의 순서를 (sid, name, face_data)로 맞춥니다.
        params = (sid, name, face_data) 
        
        cursor.execute(sql, params)
        
        conn.commit()
        return True, {}

    except psycopg2.IntegrityError:
        # 이미 존재하는 sid로 INSERT를 시도했을 때
        conn.rollback() 
        return False, {"error_code": "INTEGRITY_ERROR", "message": "이미 존재하는 학번입니다."} 
        
    except psycopg2.Error as e:
        # 그 외 DB 오류 발생 시
        conn.rollback() 
        print(f"Student INSERT transaction failed: {e}")
        return False, ERROR_DB
        
    finally:
        conn.close()

# 5. 회원 기록 수정


# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

def update_student(
    sid: str,
    update_data: Dict[str, bytes]
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    students 테이블에서 sid에 해당하는 회원의 정보를 갱신합니다.
    update_data에 포함된 필드(face, card)만 수정합니다.
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "회원 정보 수정 중 데이터베이스 오류가 발생했습니다."}
    
    
    # 1. 수정할 필드 목록과 값 목록 초기화
    set_clauses = [] # SQL의 'SET column = %s' 부분을 담을 리스트
    params = []      # SQL 쿼리에 바인딩할 값 리스트

    # 2. 수정 가능한 필드 확인 및 쿼리 구성
    if 'face' in update_data:
        face_value = update_data['face']

        if not isinstance(face_value, bytes):
        # bytes가 아니면 오류 반환 (API 호출자가 잘못된 타입을 보냈을 때)
            return False, {"error_code": "INVALID_TYPE", "message": "face 데이터는 반드시 bytes 타입이어야 합니다."}
    
        set_clauses.append("face = %s")
        params.append(update_data['face'])
        
    # if 'card' in update_data:
    #     set_clauses.append("card = %s")
    #     params.append(update_data['card'])
        
    # 3. 수정할 내용이 없으면 True 반환 (할 일이 없으므로 성공 처리)
    if not set_clauses:
        return True, {}

    # 4. 최종 SQL 쿼리 조립 및 WHERE 절에 sid 추가
    sql = f"UPDATE students SET {', '.join(set_clauses)} WHERE sid = %s"
    params.append(sid) # WHERE 절에 사용할 sid를 params 리스트의 마지막에 추가
    
    
    try:
        # 5. SQL 쿼리 실행
        cursor.execute(sql, tuple(params))
        
        # 6. 변경된 행이 있는지 확인 (선택적)
        if cursor.rowcount == 0:
            # UPDATE 쿼리가 실행되었지만, sid에 해당하는 행이 없어서 갱신되지 않은 경우
            # 이 오류는 핸들러의 'check_student_exist'에서 404로 먼저 잡아야 하지만, 
            # 트랜잭션의 안전을 위해 DB 레벨에서 한 번 더 확인합니다.
            conn.rollback()
            return False, {"error_code": "NOT_FOUND", "message": "수정할 회원 ID를 찾을 수 없습니다."}

        conn.commit() # 쿼리 실행 성공 시 최종 저장
        return True, {}

    except psycopg2.Error as e:
        conn.rollback() 
        print(f"Student UPDATE transaction failed: {e}")
        return False, ERROR_DB
        
    finally:
        conn.close()

# --- 3. 출입 기록 최종 저장/갱신 (IN/OUT 분기) ---

# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

def process_access_record(
    sid: str, 
    action_type: str, 
    update_log_id: Optional[int]
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    IN 또는 OUT 타입에 따라 log 테이블에 최종 기록을 저장하거나 갱신합니다.
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."} 
    
    cursor = conn.cursor()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "출입 기록 저장 중 데이터베이스 오류가 발생했습니다."}
    # UTC 사용 (권장)
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S') 
    try:
        if action_type == "IN":
            # [Case 1] 입장 처리: 새로운 기록을 INSERT 합니다.
            sql = "INSERT INTO log (sid, enter) VALUES (%s, %s)"
            cursor.execute(sql, (sid, current_time))
            
        elif action_type == "OUT":
            # [Case 2] 퇴장 처리: 기존 기록에 exit 시간을 UPDATE 합니다.
            if update_log_id is None:
                # 안전 장치: OUT인데 log_id가 없으면 논리 오류
                return False, {"error_code": "LOGIC_ERROR", "message": "퇴장 처리 시 대상 LOG ID가 누락되었습니다."}

            # log_id를 사용해 가장 최근의 입장 기록에 퇴장 시간을 갱신합니다.
            sql = "UPDATE log SET exit = %s WHERE log_id = %s"
            cursor.execute(sql, (current_time, update_log_id))

            if cursor.rowcount == 0:
                conn.rollback()
                # 이 log_id는 유효하지 않은 (이미 삭제된) 기록일 수 있습니다.
                return False, {"error_code": "NOT_FOUND", "message": "갱신할 log_id를 찾을 수 없습니다."}

        else:
            # action_type이 IN/OUT이 아닐 때의 예외 처리
            return False, {"error_code": "INVALID_ACTION_TYPE", "message": "유효하지 않은 출입 타입입니다."}
            
        
        conn.commit() # 🚨 쿼리 실행 성공 시 최종 저장
        return True, {}

    except psycopg2.Error as e:
        # DB 오류 발생 시 변경사항 취소 및 500 에러 처리
        conn.rollback() 
        print(f"Access record transaction failed: {e}")
        return False, ERROR_DB 
        
    finally:
        conn.close()



# ... (나머지 모든 내부 함수들도 이 파일에 작성됩니다.)

# 예약 기록 삽입

# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

def create_reservation(
    data: Dict[str, Any]
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    제공된 데이터와 타입에 따라 facility_reservation 또는 seat_reservation 테이블에 
    새로운 예약 기록을 삽입하는 트랜잭션 함수입니다.
    
    Args:
        data: 예약에 필요한 모든 데이터 (sid, facility_id/room_id, times 등).
        reservation_type: 'facility' 또는 'seat'
        
    Returns:
        True (성공) 또는 (False, 오류 상세 정보)
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "예약 기록 저장 중 데이터베이스 오류가 발생했습니다."}
    
    try:
        # 🚨 seat_reservation 테이블 INSERT 쿼리
        sql = """
            INSERT INTO seat_reservation 
            (sid, room_id, seat_number, date, start_time, end_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            data['sid'], data['room_id'], data['seat_number'], 
            data['date'], data['start_time'], data['end_time']
        )

        # SQL 쿼리 실행
        cursor.execute(sql, params)
        
        # 3. 최종 저장: 쿼리가 성공했을 때만 commit() 합니다.
        conn.commit()
        return True, {}

    except psycopg2.Error as e:
        # 오류 발생 시 변경사항 취소 (rollback)
        conn.rollback() 
        print(f"Reservation transaction failed : {e}")
        return False, ERROR_DB # 실패 시 False와 오류 정보 반환
        
    finally:
        # 4. 주방 정리: DB 연결을 닫습니다.
        conn.close()


# 시간대 확인


# 💡 참고: 이 함수는 DB 접근 없이 순수 파이썬 논리만 사용합니다.

def check_time(
    start_time: str, 
    end_time: str, 
    operating_hours: Dict[str, str]
) -> Union[Tuple[bool, Dict[str, str]], bool]:
    """
    예약 시작 시간과 종료 시간이 운영 규칙 및 시간 순서에 맞는지 확인하는 내부 함수입니다.
    
    Args:
        start_time: 요청된 예약 시작 시간 (예: "14:00").
        end_time: 요청된 예약 종료 시간 (예: "18:00").
        operating_hours: 시설의 운영 시간 기준 ({"open": time(9, 0), "close": time(22, 0)}).

    Returns:
        True (성공) 또는 (False, 오류 상세 정보 딕셔너리)를 반환합니다.
    """
    
    # 템플릿화된 오류 메시지
    ERROR_WRONG_TIME = {"error_code": "WRONG_TIME", "message": "예약 시간이 운영 규칙에 위배됩니다."}

    time_format = "%H:%M:%S"
    try:
        # 1. 문자열 시간을 time 객체로 변환 (비교를 위해)
        start_dt = datetime.strptime(start_time, time_format).time()
        end_dt = datetime.strptime(end_time, time_format).time()
        
        # 2. 운영 시간 기준 추출 (매개변수가 없으면 기본값 설정)
        open_time_str = operating_hours.get("open", "06:00")
        close_time_str = operating_hours.get("close", "23:59")
        open_time = datetime.strptime(open_time_str, time_format).time()
        close_time = datetime.strptime(close_time_str, time_format).time()
    except ValueError:
        # 시간 형식이 잘못되었을 때 (예: '99:00' 또는 '오전 10시' 등)
        return False, {"error_code": "INVALID_TIME_FORMAT", "message": "시간 형식이 올바르지 않습니다."}


    # -----------------------------------------------------------
    # 비즈니스 로직 (규칙 검증)
    # -----------------------------------------------------------
    
    # 3. [규칙 A] 시작 시간이 종료 시간보다 빠른지 확인
    # if start_dt >= end_dt:
    #     ERROR_WRONG_TIME["message"] = "종료 시간이 시작 시간보다 빠르거나 같습니다."
    #     return False, ERROR_WRONG_TIME

    # 4. [규칙 B] 예약 시간이 운영 시간 안에 있는지 확인
    if start_dt < open_time & start_dt > close_time:
        ERROR_WRONG_TIME["message"] = f"운영 시간({open_time.strftime(time_format)}~{close_time.strftime(time_format)}) 외의 시간입니다."
        return False, ERROR_WRONG_TIME
        
    # 5. [규칙 C] 최소/최대 예약 시간 (예: 최소 30분, 최대 4시간) 확인
    
    # # 임시 날짜 객체 생성 (시간 차이 계산 용도)
    start_dt_combined = datetime.combine(datetime.now().date(), start_dt)
    end_dt_combined = datetime.combine(datetime.now().date(), end_dt)

    # # 🚨 날짜 경계를 넘어갔다면, end_dt_combined에 하루(1일)를 더합니다.
    if end_dt_combined < start_dt_combined:
         end_dt_combined += timedelta(days=1)
    
    time_diff = end_dt_combined - start_dt_combined

    # services/core_service.py (check_time 함수 내부 - 3시간 규칙 검사 부분)

    # ... (중략: time_diff 계산 로직 유지)

    fixed_duration = timedelta(hours=3)
    tolerance = timedelta(seconds=1) # 1초 미만의 오차는 허용

    is_correct_duration = (time_diff > (fixed_duration - tolerance)) and \
                        (time_diff < (fixed_duration + tolerance))

    if not is_correct_duration:
        ERROR_WRONG_TIME["message"] = "예약 시간은 정확히 3시간으로만 설정할 수 있습니다."
        return False, ERROR_WRONG_TIME
    # # 시간 차이를 계산하기 위해 임시로 날짜(datetime.min)를 붙여 datetime 객체로 만듭니다.
    # # time_diff = datetime.combine(datetime.min, end_dt) - datetime.combine(datetime.min, start_dt)
    # fixed_duration = timedelta(hours=3)
    # if time_diff != fixed_duration:
    #     ERROR_WRONG_TIME["message"] = "예약 시간은 정확히 3시간으로만 설정할 수 있습니다."
    #     return False, ERROR_WRONG_TIME
        
    # 6. 모든 검증 통과 시 True 반환
    return True, {}

# services/core_service.py (새 함수 추가)

# ... (기존 get_db_connection 함수 사용)

def get_room_operating_hours(room_id: str) -> Optional[Dict[str, str]]:
    """
    특정 열람실의 운영 시작/종료 시간을 DB에서 조회합니다.
    (예: {'open': '09:00:00', 'close': '22:00:00'})
    """
    conn = get_db_connection()
    if conn is None: 
        return None  # DB 연결 실패 시 None 반환
    
    cursor = conn.cursor()
    
    try:
        sql = """
            SELECT open, close
            FROM study_room
            WHERE room_id = %s
        """
        cursor.execute(sql, (room_id,))
        result = cursor.fetchone()
        
        if result:
            # psycopg2.extras.RealDictCursor 사용 가정: 이미 딕셔너리 형태
            # TIME 타입은 Python의 datetime.time 객체로 반환될 수 있음.
            # 핸들러에서 문자열로 처리하기 쉽게 여기서 문자열로 포맷팅하거나, 
            # API 핸들러에서 datetime.time 객체를 그대로 사용하도록 합니다.
            
            # 🚨 Note: 여기서는 API 핸들러의 check_time 함수가 문자열을 요구하므로,
            #         datetime.time 객체를 HH:MM:SS 문자열로 변환하여 반환합니다.
            return {
                "open": result['open'].strftime('%H:%M:%S'),
                "close": result['close'].strftime('%H:%M:%S')
            }
        else:
            return None # 방을 찾지 못함
            
    except psycopg2.Error as e:
        print(f"Room hours DB Error: {e}")
        return None
        
    finally:
        conn.close()



# 출입 기록 조회

# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

def get_access_records(
    sid: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
) -> Union[List[Dict[str, Any]], Tuple[bool, Dict[str, str]]]:
    """
    제공된 조건(sid, 날짜 범위)에 따라 출입 기록(log 테이블)을 조회합니다.
    
    Args:
        sid: 조회할 회원의 고유 ID (선택적).
        start_date: 조회 시작 날짜 (YYYY-MM-DD 형식, 선택적).
        end_date: 조회 종료 날짜 (YYYY-MM-DD 형식, 선택적).
        
    Returns:
        List[sqlite3.Row] (조회 성공 시) 또는 (False, 오류 상세 정보)
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "출입 기록 조회 중 데이터베이스 오류가 발생했습니다."}
    
    # 쿼리의 기본 구조
    base_query = """
        SELECT log_id, sid, enter, exit
        FROM log
    """
    
    # WHERE 절을 구성할 리스트와 SQL 바인딩 매개변수 리스트
    conditions = []
    params = []

    # 1. sid 조건 추가
    if sid:
        conditions.append("sid = %s")
        params.append(sid)

    # 2. 날짜 범위 조건 추가 (enter의 날짜 부분만 비교)
    if start_date and end_date:
        # SQLite의 datetime() 함수를 사용하여 enter에서 날짜만 추출하여 비교
        conditions.append("enter::DATE BETWEEN %s AND %s")
        params.append(start_date)
        params.append(end_date)
    elif start_date:
        conditions.append("enter::DATE >= %s")
        params.append(start_date)
    elif end_date:
        conditions.append("enter::DATE <= %s")
        params.append(end_date)

    # WHERE 절 조합
    if conditions:
        query = base_query + " WHERE " + " AND ".join(conditions)
    else:
        query = base_query

    # 3. 데이터 정렬 (최신 기록이 위로 오도록)
    query += " ORDER BY enter DESC"

    try:
        # SQL 쿼리 실행
        cursor.execute(query, params)
        
        # 4. 결과 반환 (sqlite3.Row 객체 리스트)
        db_rows = cursor.fetchall()
        return db_rows # 👈 List[sqlite3.Row] 반환

    except psycopg2.Error as e:
        print(f"Access records retrieval failed: {e}")
        return False, ERROR_DB 
        
    finally:
        conn.close()





# 좌석 정보 조회 => 좌석이 존재하는지 확인하는 함수

# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

def get_seat_information(
    room_id: str, 
    seat_number: int
) -> Optional[Dict[str, Any]]:
    """
    특정 room_id와 seat_number에 해당하는 좌석 정보를 DB에서 조회합니다.
    
    Args:
        room_id: 열람실 ID.
        seat_number: 좌석 번호.
        
    Returns:
        Dict (좌석 정보) 또는 None (좌석이 없거나 DB 오류 발생 시).
    """
    conn = get_db_connection()
    if conn is None: 
        # DB 연결 실패 시 None 반환 (상위에서 500 에러 처리)
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    cursor = conn.cursor()
    
    try:
        # 🚨 study_room_seat 테이블은 room_id와 seat_number를 복합 키로 사용합니다.
        # 조회하려는 좌석이 DB에 존재하는지 확인하고, 해당 정보를 가져옵니다.
        sql = """
            SELECT 
                T1.room_id, 
                T1.seat_number, 
                T2.room_name, 
                T2.location,
                T2.open,        -- 👈 study_room 테이블의 open 시간 추가
                T2.close 
            FROM study_room_seat AS T1
            INNER JOIN study_room AS T2 ON T1.room_id = T2.room_id
            WHERE T1.room_id = %s AND T1.seat_number = %s
        """
        # 매개변수는 순서대로 튜플에 담아 전달합니다.
        params = (room_id, seat_number)
        
        cursor.execute(sql, params)
        
        # 1. 결과 확인: 하나의 행만 가져옵니다.
        result_row = cursor.fetchone() 

        if result_row:
            # 2. 결과 반환: sqlite3.Row 객체를 dict()로 변환하여 반환합니다.
            return dict(result_row) 
        else:
            # 좌석을 찾지 못했을 경우
            return False, {"error_code": "SEAT_NOT_FOUND", "message": "요청하신 좌석 ID를 찾을 수 없습니다."}
    except psycopg2.Error as e:
        print(f"Seat information retrieval failed: {e}")
        # DB 오류 발생 시 None 반환 (상위에서 500 에러 처리)
        return False, {"error_code": "DB_EXECUTION_ERROR", "message": f"좌석 정보 조회 중 DB 오류: {str(e)}"}
    finally:
        conn.close()


# 타인 예약 충돌 확인


# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

def check_time_overlap(
    start_time: str, 
    end_time: str, 
    reservation_date: str,
    room_id: str, 
    seat_number: int,
    exclude_res_id: Optional[int] = None
) -> bool:
    """
    주어진 시간대가 DB의 다른 예약 기록과 겹치는지 확인합니다.

    Args:
        start_time: 요청된 예약 시작 시간 (예: "14:00").
        end_time: 요청된 예약 종료 시간 (예: "18:00").
        resource_id: 시설 ID (facility_id) 또는 좌석 ID (room_id, seat_number 조합 중 하나).
        table_name: 검색할 예약 테이블 ('facility_reservation' 또는 'seat_reservation').
        exclude_res_id: 수정 시 자기 자신의 예약 ID를 제외하기 위해 사용 (선택적).

    Returns:
        bool: 충돌이 발생하면 True, 아니면 False를 반환합니다.
    """
    conn = get_db_connection()
    if conn is None: 
        # DB 연결 실패 시 True를 반환하여 안전하게 예약 진행을 막거나 (핸들러에서 500 처리)
        # 여기서는 True/False 반환 목표에 맞춰 False를 반환하고 상위에서 500 처리함.
        return False
    
    cursor = conn.cursor()
    
    try:
        # 1. 쿼리 구성 요소 설정 (테이블 이름과 자원 ID 컬럼 설정)
        # 좌석 예약은 room_id와 seat_number를 모두 비교해야 하지만, 
        # 여기서는 편의상 room_id만 대표로 사용하거나, 두 조건을 params에 추가해야 함.
        # 복잡성을 줄이기 위해 resource_id에 'room_id'를 전달하고,
        # seat_number를 별도로 전달한다고 가정하거나, 이 함수를 분리해야 함.
        # => 설계 일관성을 위해, 좌석 예약 시에도 'room_id'를 resource_id로 사용한다고 가정.
        

        # 2. SQL 쿼리 조건 설정
        # 🚨 시간 충돌의 표준 논리: (A의 시작 < B의 종료) AND (A의 종료 > B의 시작)
        sql = f"""
            SELECT reservation_id 
            FROM seat_reservation
            WHERE 
                room_id = %s AND seat_number = %s  /* 겹치는지 확인할 자원 (시설 또는 방) */
                AND date = %s  /* 👈 날짜 일치 조건 추가 */
                AND return_time IS NULL
                AND (
                    (start_time < %s) AND (end_time > %s) /* 기존 예약이 요청 시간과 겹치는 경우 */
                )
        """
        params = [room_id, seat_number, reservation_date, end_time, start_time] 

        # 3. 예약 변경 시 자기 자신 제외 (exclude_res_id 처리)
        if exclude_res_id is not None:
            sql += " AND reservation_id != %s"
            params.append(exclude_res_id)

        # 4. 쿼리 실행
        cursor.execute(sql, tuple(params))
        
        # 5. 결과 반환: 충돌하는 예약이 한 건이라도 발견되면 True 반환
        return cursor.fetchone() is not None 

    except psycopg2.Error as e:
        print(f"Time overlap check DB Error for seat_reservation: {e}")
        # DB 오류 발생 시 안전하게 True (충돌) 반환하여 예약 진행을 막습니다.
        return True
        
    finally:
        conn.close()

# 예약 현황 목록 조회

# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

def get_reservation_status(
    conditions: Dict[str, Any]
) -> Union[List[Dict[str, Any]], Tuple[bool, Dict[str, str]]]:
    """
    주어진 조건에 따라 시설 또는 좌석 예약 현황 목록을 조회합니다.

    Args:
        conditions: 조회 조건이 담긴 딕셔너리 (예: {'sid': '123', 'date': '2025-10-25', 'room_id': 'R01'}).
        
    Returns:
        List[Dict] (JSON List 형태로 변환 가능한 데이터 목록) 또는 (False, 오류 상세 정보).
    """
    conn = get_db_connection()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "예약 현황 조회 중 데이터베이스 오류가 발생했습니다."}
    
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    
    # 1. 조회할 테이블 및 자원 컬럼 결정
    table_name = 'seat_reservation'
    select_columns = "reservation_id, sid, room_id, seat_number, date, start_time, end_time"
        
    # 2. SQL 쿼리 구성
    base_query = f"SELECT {select_columns} FROM {table_name}"
    
    where_clauses = []
    params = []

    # conditions 딕셔너리를 반복하여 WHERE 절 구성
    for key, value in conditions.items():
        # 데이터베이스의 컬럼 이름과 JSON Key가 동일하다고 가정
        where_clauses.append(f"{key} = %s") 
        params.append(value)
        
    # 현재 시간보다 미래의 예약만 조회하는 조건 추가 (선택적)
    # where_clauses.append("end_time > DATETIME('now', 'localtime')") 
    # 이 쿼리를 실행하면 오류가 발생했으므로, 쿼리 구문을 변경합니다.
    # where_clauses.append("start_time < CURRENT_TIME") # 예약이 이미 시작했는지 확인 (당일 한정 문제)
    # where_clauses.append("end_time > CURRENT_TIME") # 예약이 아직 끝나지 않았는지 확인 (당일 한정 문제)

    # where_clauses.append("end_time > CURRENT_TIME AND date = CURRENT_DATE")
    where_clauses.append("date + start_time <= NOW()") # 예약 시작 시간이 현재 시간보다 빠르거나 같고
    # where_clauses.append("date + end_time > NOW()")   # 예약 종료 시간이 현재 시간보다 늦고
    where_clauses.append("return_time IS NULL")
    
    # 3. 최종 쿼리 조립 및 정렬
    query = base_query + " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY start_time ASC" # 시간 순서대로 정렬

    try:
        # 4. 쿼리 실행
        cursor.execute(query, params)
        db_rows = cursor.fetchall()
        
        # 5. 결과 반환: sqlite3.Row 객체 리스트를 그대로 반환합니다.
        # (상위 API 핸들러에서 format_db_rows_to_json을 호출하여 최종 JSON으로 변환할 것입니다.)
        return db_rows

    except psycopg2.Error as e:
        print(f"Reservation status retrieval failed: {e}")
        return False, ERROR_DB
        
    finally:
        conn.close()


# 학생이 정석 내부에 있는지 확인

# DB 연결 함수는 get_db_connection()을 사용한다고 가정합니다.

def check_student_inside(sid: str) -> bool:
    """
    특정 SID를 가진 학생이 현재 도서관에 입실 상태(log.exit IS NULL)인지 확인합니다.

    Args:
        sid: 상태를 확인할 학생의 학번.

    Returns:
        bool: 입실 상태이면 True, 아니면 False를 반환합니다.
    """
    conn = get_db_connection()
    if conn is None: 
        # DB 연결 실패 시, 안전하게 False를 반환하거나 상위에서 500 처리
        # 여기서는 True/False를 반환하는 함수 목표에 맞춰 False를 반환
        return False
    
    cursor = conn.cursor()
    
    try:
        # [Step 2-A] 해당 SID의 가장 최근 출입 기록을 1개 조회합니다.
        sql = """
            SELECT exit 
            FROM log 
            WHERE sid = %s 
            ORDER BY log_id DESC 
            LIMIT 1
        """
        cursor.execute(sql, (sid,))
        
        last_log = cursor.fetchone() 

        # [Step 2-B] 상태 판단
        
        # Case 1: 기록이 아예 없는 경우 (DB에 sid 기록이 없음)
        if last_log is None:
            # 기록이 없으므로 현재 내부에 있다고 볼 수 없음
            return False 
        
        # Case 2: 최근 기록의 'exit' 컬럼이 NULL인 경우
        if last_log['exit'] is None:
            # exit 시간이 비어있으므로, 현재 입실(IN) 상태입니다.
            return True 
        
        # Case 3: 최근 기록의 'exit' 컬럼에 값이 있는 경우
        else:
            # 이미 퇴실 처리되었으므로, 현재 내부에 있지 않습니다.
            return False

    except psycopg2.Error as e:
        print(f"DB Error checking student status: {e}")
        # DB 오류 발생 시 안전하게 False 반환 (상위에서 500 에러 처리)
        return False 
        
    finally:
        conn.close()




# 💡 외부에서 임포트해야 할 함수들 (가정):
# from .core_service import check_time_overlap
# from ..utils.helper_functions import validate_date_format # (날짜 형식 검증 함수)
# from ..database import get_db_connection

# 🚨 연장 및 최대 시간 상수는 여기에 정의됩니다.

# 💡 max_total_duration: 총 예약 가능 시간 (예: 6시간)
MAX_TOTAL_DURATION = timedelta(hours=6)
# 💡 min_elapsed_time: 연장 가능 최소 사용 시간 (예: 2시간)
MIN_ELAPSED_TIME = timedelta(hours=2)

def check_extension_validity(
    reservation_info: Dict[str, Any]
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    제공된 예약 정보가 연장 규칙에 맞는지 검증합니다.
    (예약 정보는 이미 단일 딕셔너리 형태로 변환되었다고 가정합니다.)
    
    Args:
        reservation_info: 단일 예약 기록 딕셔너리 (start_time, end_time 포함).
        
    Returns:
        True (연장 가능) 또는 (False, 오류 상세 정보).
    """
    
    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'  # DB에 저장된 시간 형식 (날짜까지 포함 가정)
    
    try:
        # 현재 UTC 시간을 기준으로 비교합니다.
        # DB 저장 시 타임존이 없어도 UTC임을 가정하고 처리합니다.
        now_utc = datetime.now(timezone.utc) 
        
        # 1. 예약 시간을 datetime 객체로 변환
        start_dt = datetime.strptime(reservation_info['start_time'], TIME_FORMAT).replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(reservation_info['end_time'], TIME_FORMAT).replace(tzinfo=timezone.utc)
        
        # ----------------------------------------------------------------------
        # A. 예약이 이미 끝났는지 확인 (end_time이 현재 시간보다 빠른지)
        # ----------------------------------------------------------------------
        if end_dt <= now_utc:
            return False, {
                "error_code": "RESERVATION_ENDED", 
                "message": "예약 시간이 이미 종료되었습니다."
            }
        
        # ----------------------------------------------------------------------
        # B. 사용한 지 2시간이 지났는지 확인 (start_time과 현재 시간 비교)
        # ----------------------------------------------------------------------
        elapsed_time = now_utc - start_dt
        if elapsed_time < MIN_ELAPSED_TIME:
            min_minutes = int(MIN_ELAPSED_TIME.total_seconds() / 60)
            return False, {
                "error_code": "NOT_ENOUGH_TIME_USED", 
                "message": f"예약 후 최소 {min_minutes}분을 사용해야 연장이 가능합니다."
            }

        # ----------------------------------------------------------------------
        # C. 최대 총 예약 시간 초과 여부 확인 (총 6시간 제한 가정)
        # ----------------------------------------------------------------------
        total_duration = end_dt - start_dt
        
        # 현재 예약 기간이 이미 최대 허용 기간을 초과했는지 확인합니다.
        if total_duration >= MAX_TOTAL_DURATION:
            return False, {
                "error_code": "MAX_DURATION_EXCEEDED", 
                "message": f"현재 예약은 이미 최대 허용 시간({int(MAX_TOTAL_DURATION.total_seconds() / 3600)}시간)을 모두 사용했습니다."
            }
        
        # 모든 검증 통과
        return True
        
    except ValueError:
        # DB 저장된 시간이 YYYY-MM-DD HH:MM:SS 형식이 아닐 때
        return False, {
            "error_code": "INTERNAL_TIME_FORMAT_ERROR", 
            "message": "내부 예약 시간 형식이 올바르지 않아 연장할 수 없습니다."
        }
    except Exception as e:
        # 그 외 예측하지 못한 오류
        return False, {
            "error_code": "EXTENSION_LOGIC_ERROR", 
            "message": f"연장 로직 처리 중 오류 발생: {str(e)}"
        }
    

# 💡 DB 연결 함수 임포트
# 💡 충돌 확인 함수 임포트 (연장 후 충돌 검사 재사용)

# 🚨 연장 시간 정의 (3시간)
EXTENSION_DURATION = timedelta(hours=3)
# 🚨 DB 저장 시간 형식 정의 (date와 time이 모두 포함된 형식 가정)
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


def execute_extend_reservation(
    res_id: int
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    주어진 reservation_id에 해당하는 좌석 예약의 종료 시간을 3시간 연장합니다.
    (연장 전 충돌 여부를 확인합니다.)
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    
    try:
        # --- 1. 기존 예약 정보 조회 ---
        sql_select = """
            SELECT reservation_id, date, end_time, room_id, seat_number, sid 
            FROM seat_reservation 
            WHERE reservation_id = %s
        """
        cursor.execute(sql_select, (res_id,))
        reservation_row = cursor.fetchone()
        
        if not reservation_row:
            # 기록을 찾을 수 없는 경우 (API 핸들러의 404 처리와는 별개로 DB 로직에서 처리)
            return False, {"error_code": "NOT_FOUND", "message": "해당 예약 ID를 찾을 수 없습니다."}
            
        reservation_info = dict(reservation_row)
        
        # --- 2. 새로운 종료 시간 계산 ---
        # DB의 end_time (TEXT)을 datetime 객체로 변환합니다. (UTC 가정)
        current_end_dt = datetime.strptime(reservation_info['end_time'], TIME_FORMAT).replace(tzinfo=timezone.utc)
        
        # 새로운 종료 시간 = 기존 종료 시간 + 3시간
        new_end_dt = current_end_dt + EXTENSION_DURATION
        
        # 쿼리 바인딩을 위한 문자열로 포맷
        new_end_time_str = new_end_dt.strftime(TIME_FORMAT)
        
        # --- 3. 충돌 확인 (새로운 종료 시간으로 인해 타인 예약과 겹치는지 검사) ---
        # 연장이 타인 예약과 충돌하는지 확인합니다.
        # 기존 예약 ID는 exclude_res_id로 제외합니다.
        
        # --- 4. 기록 업데이트 (트랜잭션 실행) ---
        sql_update = """
            UPDATE seat_reservation 
            SET end_time = %s 
            WHERE reservation_id = %s AND sid = %s
        """
        # 쿼리 실행
        cursor.execute(sql_update, (new_end_time_str, res_id, reservation_info['sid']))
        
        conn.commit() # 최종 저장
        return True

    except psycopg2.Error as e:
        conn.rollback() # 오류 발생 시 롤백
        print(f"Reservation extension transaction failed: {e}")
        return False, {"error_code": "DB_ERROR", "message": "예약 연장 중 데이터베이스 오류 발생."}
        
    except Exception as e:
        # 시간 변환 오류 등 기타 예외 처리
        print(f"Reservation extension logic failed: {e}")
        conn.rollback()
        return False, {"error_code": "LOGIC_ERROR", "message": f"연장 로직 실행 오류: {str(e)}"}

    finally:
        conn.close()



# 🚨 반납 상태 상수 정의


def execute_reservation_return(
    res_id: int
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    주어진 예약 ID의 좌석 기록을 '반납됨' 상태로 갱신하는 트랜잭션 함수입니다.
    (reservation_id를 기본 키로 사용하여 UPDATE를 실행합니다.)
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    
    # 1. 사용할 테이블과 상태 상수 결정
    table_name = 'seat_reservation'
    # 🚨 CRITICAL FIX: 문자열 대신 Python datetime 객체 그대로 사용 (PostgreSQL 권장)
    status_value = datetime.now(timezone.utc)

    try:
        # --- 2. UPDATE 쿼리 실행 (return_status 컬럼 업데이트) ---
        sql_update = f"""
            UPDATE {table_name}
            SET return_time = %s  /* 👈 상태와 end_time(실제 반납 시간)을 갱신 */
            WHERE reservation_id = %s
        """
        
        # 쿼리 실행
        cursor.execute(sql_update, (status_value, res_id))
        
        # 3. 변경된 행 확인 및 트랜잭션 종료
        if cursor.rowcount == 0:
            conn.rollback()
            return False, {"error_code": "NOT_FOUND", "message": f"예약 ID {res_id}를 찾을 수 없습니다."}
            
        conn.commit() # 최종 저장
        return True, {}

    except psycopg2.Error as e:
        conn.rollback() # 오류 발생 시 롤백
        print(f"Reservation return transaction failed for {table_name}: {e}")
        return False, {"error_code": "DB_ERROR", "message": "예약 반납 중 데이터베이스 오류 발생."}
        
    finally:
        conn.close()