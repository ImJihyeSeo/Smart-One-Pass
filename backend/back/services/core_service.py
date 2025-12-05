from typing import Union, Dict, Any, Tuple, Optional, List
from datetime import datetime, timezone, timedelta
import psycopg2
from dotenv import load_dotenv
import numpy as np
from database import get_db_connection 

load_dotenv()
# ✅ [추가] 전역 KST 상수 정의
KST = timezone(timedelta(hours=9))


# 1. 회원 존재 확인
def check_student_exists(sid: str) -> bool:
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()

        # sid를 이용해 students 테이블에서 sid를 조회
        sql = "SELECT sid FROM students WHERE sid = %s"
        cursor.execute(sql, (sid,))

        result = cursor.fetchone()

        return result is not None

    except psycopg2.Error as e:
        print(f"Error checking user existence: {e}")
        return False
	
    finally:
        conn.close()


# 2. DB에 있는지 확인
def prev_check_student(sid: str, name: str) -> bool:
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        
        # sid가 일치하거나 OR name이 일치하는 레코드가 있는지 조회합니다.
        sql = "SELECT sid FROM students WHERE sid = %s OR name = %s"
        
        # sid와 name을 모두 전달합니다.
        cursor.execute(sql, (sid, name))

        result = cursor.fetchone()

        # 결과가 있으면 중복이므로 True 반환
        return result is not None

    except psycopg2.Error as e:
        print(f"Error checking user existence: {e}")
        return False
    
    finally:
        conn.close()



# 3. 회원 기록 삭제
def execute_delete_students(sid: str) -> bool:
    conn = get_db_connection()
    if conn is None:
        return False 
    
    try:
        cursor = conn.cursor()
                
        # 1) 예약 기록 삭제
        cursor.execute("DELETE FROM seat_reservation WHERE sid = %s", (sid,))
        
        # 2) 출입 기록 삭제
        cursor.execute("DELETE FROM log WHERE sid = %s", (sid,))
        
        # 3) 회원 기록 최종 삭제
        cursor.execute("DELETE FROM students WHERE sid = %s", (sid,))
        
        conn.commit()
        return True, {}

    except psycopg2.Error as e:
        print(f"User deletion failed: {e}")
        conn.rollback()
        return False, {}
        
    finally:
        conn.close()


# 4. 얼굴 데이터가 일치하는 sid 찾기
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
    
    # 유사도 기준값 0.29
    SIMILARITY_THRESHOLD = 0.29 
    
    try:
        # 1) 입력된 bytes를 numpy 배열로 변환
        target_emb = np.frombuffer(face, dtype=np.float32)
        
        # 2) DB에서 모든 회원의 얼굴 데이터 가져오기
        cursor.execute("SELECT sid, face FROM students WHERE face IS NOT NULL")
        all_students = cursor.fetchall()

        max_score = -1.0
        found_sid = None

        for row in all_students:
            db_face_bytes = row['face']
            
            # DB 데이터를 numpy 배열로 변환
            db_emb = np.frombuffer(db_face_bytes, dtype=np.float32)
            
            # 3) 코사인 유사도 계산
            score = np.dot(target_emb, db_emb)
            
            # 가장 높은 점수 찾기
            if score > max_score:
                max_score = score
                found_sid = row['sid']

        print(f"🔍 [Face Auth] Max Score: {max_score}, User: {found_sid}")

        # 4) 임계값 (Threshold) 넘었는지 확인
        if found_sid and max_score >= SIMILARITY_THRESHOLD:
            return found_sid
        else:
            return False, ERROR_NOT_FOUND

    except Exception as e:
        print(f"Face check Logic Error: {e}")
        return False, {"error_code": "LOGIC_ERROR", "message": f"얼굴 비교 중 오류: {str(e)}"}
        
    finally:
        conn.close()


# 5. 상태 판단 (최근 기록에 EXIT이 NULL인지 확인)

ACTION_IN = "IN"
ACTION_OUT = "OUT"

def check_access_of_student(
    recent_log: Optional[Dict[str, Any]]
) -> Tuple[str, Optional[int]]:
    """
    현재 DB 상태(최근 로그)를 분석하여 다음에 실행해야 할 동작(IN/OUT)과 
    갱신이 필요할 경우 해당 log_id를 추론하여 반환
    """
    
    # log_id는 퇴장 시 UPDATE 대상을 지정하기 위해 필요
    log_id_to_update = None
        
    # Case 1) DB에 해당 학생의 출입 기록이 전혀 없는 경우
    if recent_log is None:
        # 이전에 기록이 없으므로, 다음 동작은 무조건 입장(IN)
        return ACTION_IN, None
        
    # Case 2) 최근 기록 확인
    # exit이 NULL인지 확인 (None이면 현재 입실 상태라는 뜻)
    recent_exit = recent_log.get('exit') 
    
    # 2-A) 현재 입실 상태인 경우
    if recent_exit is None:
        # 현재 도서관 내부에 있으므로, 다음 동작은 퇴장(OUT)
        log_id_to_update = recent_log.get('log_id')
        
        # 퇴장 처리 시, 갱신할 log_id를 함께 반환
        return ACTION_OUT, log_id_to_update
        
    # 2-B) 현재 퇴실 상태인 경우
    else:
        # 이미 퇴장까지 완료했으므로, 다음 동작은 입장(IN)
        return ACTION_IN, None



# 6. 회원 기록 저장
def execute_insert_student(
    sid: str,
    name: str,                         
    face_data: Optional[bytes] = None 
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    students 테이블에 새로운 회원 기록(sid, name, face_data)을 삽입하는 트랜잭션 함수
    """
    
    if not sid or not name: 
        return False, {"error_code": "INPUT_REQUIRED", "message": "학번(sid)과 이름(name)은 필수입니다."}

    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    cursor = conn.cursor()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "회원 기록 저장 중 데이터베이스 오류가 발생했습니다."}
    
    try:
        sql = """
            INSERT INTO students (sid, name, face)
            VALUES (%s, %s, %s)
        """
        params = (sid, name, face_data) 
        
        cursor.execute(sql, params)
        
        conn.commit()
        return True, {}

    except psycopg2.IntegrityError:
        conn.rollback() 
        return False, {"error_code": "INTEGRITY_ERROR", "message": "이미 존재하는 학번입니다."} 
        
    except psycopg2.Error as e:
        conn.rollback() 
        print(f"Student INSERT transaction failed: {e}")
        return False, ERROR_DB
        
    finally:
        conn.close()



# 7. 회원 기록 수정
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
    
    
    # 1) 수정할 필드 목록과 값 목록 초기화
    set_clauses = [] 
    params = []      

    # 2) 수정 가능한 필드 확인 및 쿼리 구성
    if 'face' in update_data:
        face_value = update_data['face']

        if not isinstance(face_value, bytes):
            return False, {"error_code": "INVALID_TYPE", "message": "face 데이터는 반드시 bytes 타입이어야 합니다."}
    
        set_clauses.append("face = %s")
        params.append(update_data['face'])
        
        
    # 3) 수정할 내용이 없으면 True 반환 (할 일이 없으므로 성공 처리)
    if not set_clauses:
        return True, {}

    # 4) 최종 SQL 쿼리 조립 및 WHERE 절에 sid 추가
    sql = f"UPDATE students SET {', '.join(set_clauses)} WHERE sid = %s"
    params.append(sid)
    
    
    try:
        # 5) SQL 쿼리 실행
        cursor.execute(sql, tuple(params))
        
        # 6) 변경된 행이 있는지 확인
        if cursor.rowcount == 0:
            conn.rollback()
            return False, {"error_code": "NOT_FOUND", "message": "수정할 회원 ID를 찾을 수 없습니다."}

        conn.commit()
        return True, {}

    except psycopg2.Error as e:
        conn.rollback() 
        print(f"Student UPDATE transaction failed: {e}")
        return False, ERROR_DB
        
    finally:
        conn.close()



# 8. 출입 기록 최종 저장/갱신 (IN/OUT 분기)
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
    
    current_time = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S') 
    try:
        if action_type == "IN":
            # Case 1) 입장 처리: 새로운 기록을 INSERT
            sql = "INSERT INTO log (sid, enter) VALUES (%s, %s)"
            cursor.execute(sql, (sid, current_time))
            
        elif action_type == "OUT":
            # Case 2) 퇴장 처리: 기존 기록에 exit 시간을 UPDATE
            if update_log_id is None:
                return False, {"error_code": "LOGIC_ERROR", "message": "퇴장 처리 시 대상 LOG ID가 누락되었습니다."}

            # log_id를 사용해 가장 최근의 입장 기록에 퇴장 시간을 갱신
            sql = "UPDATE log SET exit = %s WHERE log_id = %s"
            cursor.execute(sql, (current_time, update_log_id))

            if cursor.rowcount == 0:
                conn.rollback()
                return False, {"error_code": "NOT_FOUND", "message": "갱신할 log_id를 찾을 수 없습니다."}

        else:
            return False, {"error_code": "INVALID_ACTION_TYPE", "message": "유효하지 않은 출입 타입입니다."}
            
        
        conn.commit()
        return True, {}

    except psycopg2.Error as e:
        conn.rollback() 
        print(f"Access record transaction failed: {e}")
        return False, ERROR_DB 
        
    finally:
        conn.close()




# 9. 예약 기록 삽입
def create_reservation(
    data: Dict[str, Any]
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    제공된 데이터와 타입에 따라 facility_reservation 또는 seat_reservation 테이블에 
    새로운 예약 기록을 삽입하는 트랜잭션 함수입니다.
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "예약 기록 저장 중 데이터베이스 오류가 발생했습니다."}
    
    try:
        sql = """
            INSERT INTO seat_reservation 
            (sid, room_id, seat_number, date, start_time, end_time)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (
            data['sid'], data['room_id'], data['seat_number'], 
            data['date'], data['start_time'], data['end_time']
        )

        cursor.execute(sql, params)
        
        conn.commit()
        return True, {}

    except psycopg2.Error as e:
        conn.rollback() 
        print(f"Reservation transaction failed : {e}")
        return False, ERROR_DB
        
    finally:
        conn.close()


# 10. 시간대 확인
def check_time(
    start_time: str, 
    end_time: str, 
    operating_hours: Dict[str, str]
) -> Union[Tuple[bool, Dict[str, str]], bool]:
    """
    예약 시작 시간과 종료 시간이 운영 규칙 및 시간 순서에 맞는지 확인하는 내부 함수입니다.
    """
    
    ERROR_WRONG_TIME = {"error_code": "WRONG_TIME", "message": "예약 시간이 운영 규칙에 위배됩니다."}

    time_format = "%H:%M:%S"
    try:
        # 1) 문자열 시간을 time 객체로 변환 (비교를 위해)
        start_dt = datetime.strptime(start_time, time_format).time()
        end_dt = datetime.strptime(end_time, time_format).time()
        
        # 2) 운영 시간 기준 추출 (매개변수가 없으면 기본값 설정)
        open_time_str = operating_hours.get("open", "06:00")
        close_time_str = operating_hours.get("close", "23:59")
        open_time = datetime.strptime(open_time_str, time_format).time()
        close_time = datetime.strptime(close_time_str, time_format).time()
    except ValueError:
        return False, {"error_code": "INVALID_TIME_FORMAT", "message": "시간 형식이 올바르지 않습니다."}

    # 3) 예약 시간이 운영 시간 안에 있는지 확인
    if start_dt < open_time or start_dt > close_time:
        ERROR_WRONG_TIME["message"] = f"운영 시간({open_time.strftime(time_format)}~{close_time.strftime(time_format)}) 외의 시간입니다."
        return False, ERROR_WRONG_TIME
        
       
    start_dt_combined = datetime.combine(datetime.now().date(), start_dt)
    end_dt_combined = datetime.combine(datetime.now().date(), end_dt)

    if end_dt_combined < start_dt_combined:
         end_dt_combined += timedelta(days=1)
    
    time_diff = end_dt_combined - start_dt_combined

    fixed_duration = timedelta(hours=3)
    tolerance = timedelta(seconds=1) # 1초 미만의 오차는 허용

    is_correct_duration = (time_diff > (fixed_duration - tolerance)) and \
                        (time_diff < (fixed_duration + tolerance))

    if not is_correct_duration:
        ERROR_WRONG_TIME["message"] = "예약 시간은 정확히 3시간으로만 설정할 수 있습니다."
        return False, ERROR_WRONG_TIME
        
    return True, {}


# 11. 운영 시간 확인
def get_room_operating_hours(room_id: str) -> Optional[Dict[str, str]]:
    """
    특정 열람실의 운영 시작/종료 시간을 DB에서 조회합니다.
    (예: {'open': '09:00:00', 'close': '22:00:00'})
    """
    conn = get_db_connection()
    if conn is None: 
        return None 
    
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
            return {
                "open": result['open'].strftime('%H:%M:%S'),
                "close": result['close'].strftime('%H:%M:%S')
            }
        else:
            return None
            
    except psycopg2.Error as e:
        print(f"Room hours DB Error: {e}")
        return None
        
    finally:
        conn.close()



# 12. 출입 기록 조회
def get_access_records(
    sid: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
) -> Union[List[Dict[str, Any]], Tuple[bool, Dict[str, str]]]:
    """
    제공된 조건(sid, 날짜 범위)에 따라 출입 기록(log 테이블)을 조회합니다.
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "출입 기록 조회 중 데이터베이스 오류가 발생했습니다."}
    
    base_query = """
        SELECT log_id, sid, enter, exit
        FROM log
    """
    
    conditions = []
    params = []

    # 1) sid 조건 추가
    if sid:
        conditions.append("sid = %s")
        params.append(sid)

    # 2) 날짜 범위 조건 추가 (enter의 날짜 부분만 비교)
    if start_date and end_date:
        conditions.append("enter::DATE BETWEEN %s AND %s")
        params.append(start_date)
        params.append(end_date)
    elif start_date:
        conditions.append("enter::DATE >= %s")
        params.append(start_date)
    elif end_date:
        conditions.append("enter::DATE <= %s")
        params.append(end_date)

    if conditions:
        query = base_query + " WHERE " + " AND ".join(conditions)
    else:
        query = base_query

    # 3) 데이터 정렬 (최신 기록이 위로 오도록)
    query += " ORDER BY enter DESC"

    try:
        cursor.execute(query, params)
        
        # 4) 결과 반환
        db_rows = cursor.fetchall()
        return db_rows

    except psycopg2.Error as e:
        print(f"Access records retrieval failed: {e}")
        return False, ERROR_DB 
        
    finally:
        conn.close()





# 13. 좌석 정보 조회
def get_seat_information(
    room_id: str, 
    seat_number: int
) -> Optional[Dict[str, Any]]:
    """
    특정 room_id와 seat_number에 해당하는 좌석 정보를 DB에서 조회합니다.
    """
    conn = get_db_connection()
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    cursor = conn.cursor()
    
    try:
        sql = """
            SELECT 
                T1.room_id, 
                T1.seat_number, 
                T2.room_name, 
                T2.location,
                T2.open,       
                T2.close 
            FROM study_room_seat AS T1
            INNER JOIN study_room AS T2 ON T1.room_id = T2.room_id
            WHERE T1.room_id = %s AND T1.seat_number = %s
        """
        
        params = (room_id, seat_number)
        
        cursor.execute(sql, params)
        
        result_row = cursor.fetchone() 

        if result_row:
            return dict(result_row) 
        else:
            return False, {"error_code": "SEAT_NOT_FOUND", "message": "요청하신 좌석 ID를 찾을 수 없습니다."}
    except psycopg2.Error as e:
        print(f"Seat information retrieval failed: {e}")
        return False, {"error_code": "DB_EXECUTION_ERROR", "message": f"좌석 정보 조회 중 DB 오류: {str(e)}"}
    finally:
        conn.close()


# 14. 타인 예약 충돌 확인
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
    """
    conn = get_db_connection()
    if conn is None: 
        return False
    
    cursor = conn.cursor()
    
    try:
        sql = f"""
            SELECT reservation_id 
            FROM seat_reservation
            WHERE 
                room_id = %s AND seat_number = %s
                AND date = %s
                AND return_time IS NULL
                AND (
                    (start_time < %s) AND (end_time > %s)
                )
        """
        params = [room_id, seat_number, reservation_date, end_time, start_time] 

        if exclude_res_id is not None:
            sql += " AND reservation_id != %s"
            params.append(exclude_res_id)

        cursor.execute(sql, tuple(params))
        
        return cursor.fetchone() is not None 

    except psycopg2.Error as e:
        print(f"Time overlap check DB Error for seat_reservation: {e}")
        return True
        
    finally:
        conn.close()

# 15. 예약 현황 목록 조회
def get_reservation_status(
    conditions: Dict[str, Any]
) -> Union[List[Dict[str, Any]], Tuple[bool, Dict[str, str]]]:
    """
    주어진 조건에 따라 시설 또는 좌석 예약 현황 목록을 조회합니다.
    """
    conn = get_db_connection()
    ERROR_DB = {"error_code": "DB_ERROR", "message": "예약 현황 조회 중 데이터베이스 오류가 발생했습니다."}
    
    if conn is None: 
        return False, {"error_code": "DB_CONNECTION_ERROR", "message": "데이터베이스 연결에 실패했습니다."}
    
    cursor = conn.cursor()
    
    table_name = 'seat_reservation'
    select_columns = "reservation_id, sid, room_id, seat_number, date, start_time, end_time"
        
    base_query = f"SELECT {select_columns} FROM {table_name}"
    
    where_clauses = []
    params = []

    for key, value in conditions.items():
        where_clauses.append(f"{key} = %s") 
        params.append(value)
        
    where_clauses.append("return_time IS NULL")
    
    query = base_query + " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY start_time ASC"

    try:
        cursor.execute(query, params)
        db_rows = cursor.fetchall()
        
        return db_rows

    except psycopg2.Error as e:
        print(f"Reservation status retrieval failed: {e}")
        return False, ERROR_DB
        
    finally:
        conn.close()


# 16. 학생이 정석 내부에 있는지 확인
def check_student_inside(sid: str) -> bool:
    """
    특정 SID를 가진 학생이 현재 도서관에 입실 상태(log.exit IS NULL)인지 확인합니다.
    """
    conn = get_db_connection()
    if conn is None: 
        return False
    
    cursor = conn.cursor()
    
    try:
        # 1) 해당 SID의 가장 최근 출입 기록을 1개 조회합니다.
        sql = """
            SELECT exit 
            FROM log 
            WHERE sid = %s 
            ORDER BY log_id DESC 
            LIMIT 1
        """
        cursor.execute(sql, (sid,))
        
        last_log = cursor.fetchone() 

        # 2) 상태 판단
        
        # Case 1) 기록이 아예 없는 경우 (DB에 sid 기록이 없음)
        if last_log is None:
            return False 
        
        # Case 2) 최근 기록의 'exit' 컬럼이 NULL인 경우
        if last_log['exit'] is None:
            return True 
        
        # Case 3) 최근 기록의 'exit' 컬럼에 값이 있는 경우
        else:
            return False

    except psycopg2.Error as e:
        print(f"DB Error checking student status: {e}")
        return False 
        
    finally:
        conn.close()





# 17. 좌석 예약 연장 여부 확인
MAX_TOTAL_DURATION = timedelta(hours=6)
MIN_ELAPSED_TIME = timedelta(hours=2)

def check_extension_validity(
    reservation_info: Dict[str, Any]
) -> Union[bool, Tuple[bool, Dict[str, str]]]:
    """
    제공된 예약 정보가 연장 규칙에 맞는지 검증합니다.
    (예약 정보는 이미 단일 딕셔너리 형태로 변환되었다고 가정합니다.)
    """
    
    TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    try:
        now_kst = datetime.now(KST) 


        FULL_FORMAT = '%Y-%m-%d %H:%M:%S'
        start_val = reservation_info['start_time']
        end_val = reservation_info['end_time']
        
        if isinstance(start_val, str):
            start_dt = datetime.strptime(start_val, FULL_FORMAT).replace(tzinfo=KST)
        else:
            start_dt = start_val.replace(tzinfo=KST) if start_val.tzinfo is None else start_val

        if isinstance(end_val, str):
            end_dt = datetime.strptime(end_val, FULL_FORMAT).replace(tzinfo=KST)
        else:
            end_dt = end_val.replace(tzinfo=KST) if end_val.tzinfo is None else end_val
        
        # 1. 예약이 이미 끝났는지 확인 (end_time이 현재 시간보다 빠른지)
        if end_dt <= now_kst:
            return False, {
                "error_code": "RESERVATION_ENDED", 
                "message": "예약 시간이 이미 종료되었습니다."
            }
        
        # 2. 사용한 지 2시간이 지났는지 확인 (start_time과 현재 시간 비교)
        elapsed_time = now_kst - start_dt
        if elapsed_time < MIN_ELAPSED_TIME:
            min_minutes = int(MIN_ELAPSED_TIME.total_seconds() / 60)
            return False, {
                "error_code": "NOT_ENOUGH_TIME_USED", 
                "message": f"예약 후 최소 {min_minutes}분을 사용해야 연장이 가능합니다."
            }

        # 3. 최대 총 예약 시간 초과 여부 확인 (총 6시간 제한 가정)
        total_duration = end_dt - start_dt
        
        if total_duration >= MAX_TOTAL_DURATION:
            return False, {
                "error_code": "MAX_DURATION_EXCEEDED", 
                "message": f"현재 예약은 이미 최대 허용 시간({int(MAX_TOTAL_DURATION.total_seconds() / 3600)}시간)을 모두 사용했습니다."
            }
        
        return True, {}
        
    except ValueError:
        return False, {
            "error_code": "INTERNAL_TIME_FORMAT_ERROR", 
            "message": "내부 예약 시간 형식이 올바르지 않아 연장할 수 없습니다."
        }
    except Exception as e:
        return False, {
            "error_code": "EXTENSION_LOGIC_ERROR", 
            "message": f"연장 로직 처리 중 오류 발생: {str(e)}"
        }
    

# 18. 연장 처리

EXTENSION_DURATION = timedelta(hours=3)
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
        sql_select = """
            SELECT reservation_id, date, end_time, room_id, seat_number, sid 
            FROM seat_reservation 
            WHERE reservation_id = %s
        """
        cursor.execute(sql_select, (res_id,))
        reservation_row = cursor.fetchone()
        
        if not reservation_row:
            return False, {"error_code": "NOT_FOUND", "message": "해당 예약 ID를 찾을 수 없습니다."}
            
        reservation_info = dict(reservation_row)

        FULL_FORMAT = '%Y-%m-%d %H:%M:%S'
        
        end_val = reservation_info['end_time']
        
        if isinstance(end_val, str):
            current_end_dt = datetime.strptime(end_val, FULL_FORMAT).replace(tzinfo=KST)
        else:
            current_end_dt = end_val.replace(tzinfo=KST) if end_val.tzinfo is None else end_val
            
        new_end_dt = current_end_dt + EXTENSION_DURATION
        
        new_end_time_str = new_end_dt.strftime(FULL_FORMAT)

        sql_update = """
            UPDATE seat_reservation 
            SET end_time = %s 
            WHERE reservation_id = %s AND sid = %s
        """
        cursor.execute(sql_update, (new_end_time_str, res_id, reservation_info['sid']))
        
        conn.commit()
        return True

    except psycopg2.Error as e:
        conn.rollback()
        print(f"Reservation extension transaction failed: {e}")
        return False, {"error_code": "DB_ERROR", "message": "예약 연장 중 데이터베이스 오류 발생."}
        
    except Exception as e:
        print(f"Reservation extension logic failed: {e}")
        conn.rollback()
        return False, {"error_code": "LOGIC_ERROR", "message": f"연장 로직 실행 오류: {str(e)}"}

    finally:
        conn.close()




# 19. 반납 처리
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
    
    table_name = 'seat_reservation'
    status_value = datetime.now(KST)

    try:
        sql_update = f"""
            UPDATE {table_name}
            SET return_time = %s
            WHERE reservation_id = %s
        """
        
        cursor.execute(sql_update, (status_value, res_id))
        
        if cursor.rowcount == 0:
            conn.rollback()
            return False, {"error_code": "NOT_FOUND", "message": f"예약 ID {res_id}를 찾을 수 없습니다."}
            
        conn.commit()
        return True, {}

    except psycopg2.Error as e:
        conn.rollback()
        print(f"Reservation return transaction failed for {table_name}: {e}")
        return False, {"error_code": "DB_ERROR", "message": "예약 반납 중 데이터베이스 오류 발생."}
        
    finally:
        conn.close()


# 20. 미반납 좌석 처리
def execute_auto_return():
    """
    현재 시간보다 end_time이 지난 예약들을 찾아 자동으로 '반납' 처리합니다.
    """
    print("[Auto Return] 자동 반납 검사 시작")
    
    conn = get_db_connection()
    if conn is None:
        print("[Auto Return] DB 연결 실패")
        return

    cursor = conn.cursor()
    
    try:
        now_kst = datetime.now(KST)
        current_time_str = now_kst.strftime('%Y-%m-%d %H:%M:%S')
        
        sql = """
            UPDATE seat_reservation
            SET return_time = %s
            WHERE return_time IS NULL AND end_time < %s
        """
        
        cursor.execute(sql, (current_time_str, current_time_str))
        count = cursor.rowcount 

        if count > 0:
            conn.commit()
            print(f"✅ [Auto Return] 시간이 만료된 좌석 {count}개를 강제 반납 처리했습니다.")
        else:
            print("[Auto Return] 만료된 좌석이 없습니다.")
            
    except Exception as e:
        print(f"❌ [Auto Return] 오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()