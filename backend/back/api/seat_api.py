# api/reservation_api.py (출입, 예약 조회 및 반납)
from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, Any, Optional, List
from ..services.core_service import check_student_exists, execute_delete_students, get_student_ID_by_face, check_access_of_student, execute_insert_student, update_student, process_access_record, create_reservation, check_time, get_access_records, get_seat_information, check_time_overlap, get_reservation_status, check_student_inside, check_extension_validity, execute_extend_reservation, execute_reservation_return, get_room_operating_hours
from ..utils.helper_functions import error_response, success_response, format_db_rows_to_json, validate_input
import base64
from datetime import datetime, timedelta, timezone

from database import get_db_connection # database.py에 정의된 초기화 함수 임포트

router = APIRouter()

# 좌석 예약



@router.post("/reserve")
async def reserve_seat_handler(data: Dict[str, Any]):
    """
    [API Handler] 좌석 예약 요청을 처리하고 다중 검증을 실행합니다.
    """
    
    # --- 1. 값 추출 및 유효성 검사 (DB X - Block 2) ---
    required_keys = ['sid', 'room_id', 'seat_number']
    if not validate_input(data, required_keys): 
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
        
    sid_found = data.get('sid')
    room_id = data.get('room_id')
    seat_number = data.get('seat_number')
    
    if sid_found is None:
        # validate_input이 실패했을 때 400이 발생했어야 하지만, 
        # 이 경로로 왔다는 것은 sid 키는 있지만 값이 None이라는 뜻입니다.
        raise HTTPException(status_code=400, detail="SID_CANNOT_BE_NULL")
    
    # 2. 얼굴 인증 및 SID 획득 (SELECT)
    # result = get_student_ID_by_face(face_data)
    # if isinstance(result, tuple):
    #     # NOT_FOUND 또는 DB 오류 발생 시 404/500 반환
    #     raise HTTPException(status_code=404, detail=result[1].get('error_code'))
    
    # sid_found = result # 인증된 sid


    # 🚨 추가: sid가 DB에 존재하는지 확인 (인증이 분리되었으므로 필수)
    if not check_student_exists(sid_found): 
        # 🚨 수정: 오류 코드를 명확히 지정하여 반환
        raise HTTPException(
            status_code=404, 
            detail=error_response(
                error_code="USER_NOT_FOUND", 
                message=f"학번 {sid_found}는 등록되지 않은 회원입니다."
            )
        )
    # 2-C. 예약하려는 좌석의 존재 여부 확인 (SELECT)
# 2-C. 예약하려는 좌석의 존재 여부 확인 (SELECT)
    result = get_seat_information(room_id, seat_number)
    
    if isinstance(result, tuple):
        error_details = result[1]
        error_code = error_details.get('error_code')
        
        # 🚨 NOT_FOUND와 DB_ERROR를 구분하여 처리합니다.
        if error_code in ["DB_CONNECTION_ERROR", "DB_EXECUTION_ERROR"]:
            raise HTTPException(status_code=500, detail=error_code)
            
        # 좌석이 없는 경우 404 반환
        raise HTTPException(status_code=404, detail="SEAT_NOT_FOUND")

    # 3. 시간 자동 계산 (현재 시간 기준 3시간 예약)
    # now_kst = datetime.now()
    # reservation_date = now_kst.strftime('%Y-%m-%d')
    # start_time_str = now_kst.strftime('%H:%M:%S')
    
    # 🚨 수정: KST 타임존을 명확히 지정하여 현재 시간을 얻습니다.
#          (PostgreSQL은 UTC를 선호하지만, 로컬 테스트의 일관성을 위해)
    KST = timezone(timedelta(hours=9)) 
    now_kst = datetime.now(KST)

    reservation_date = now_kst.strftime('%Y-%m-%d')
    # start_time_str = now_kst.strftime('%H:%M:%S')
    
    FULL_FORMAT = '%Y-%m-%d %H:%M:%S'
    start_time_str = now_kst.strftime(FULL_FORMAT)

    end_time_dt = now_kst + timedelta(hours=3)

    end_time_str = end_time_dt.strftime(FULL_FORMAT)

    # 3시간 후 계산 (날짜가 바뀌는 경우는 일단 무시)
    # end_time_str = end_time_dt.strftime('%H:%M:%S')
    # end_time_str = end_time_dt.strftime('%H:%M:%S')

    # 4. 운영 시간 및 예약 가능 시간 검증 (check_time)
    operating_hours = get_room_operating_hours(room_id) # core_service에서 운영 시간을 가져와야 함

    if operating_hours is None:
        raise HTTPException(status_code=404, detail="ROOM_NOT_FOUND")
    
    success, error_details = check_time(start_time_str, end_time_str, operating_hours)

    if not success:
        # 🚨 check_time 내부에서 WRONG_TIME 또는 OPERATING_HOURS_VIOLATION 오류 처리
        raise HTTPException(status_code=409, detail=error_details.get('error_code'))
        
    # 5. 시간 충돌 검사 (check_time_overlap)
    # 예약이 겹치는지 DB를 확인 (SELECT)
    # if check_time_overlap(room_id, seat_number, reservation_date, start_time_str, end_time_str):
    #     raise HTTPException(status_code=409, detail="ALREADY_RESERVED_OVERLAP")


    # 5. 시간 충돌 검사 (check_time_overlap)
    # 🚨 CRITICAL FIX: check_time_overlap의 매개변수를 DB에 맞게 전달
    if check_time_overlap(
        start_time_str,      # 🚨 시작 시간 (TIME)
        end_time_str,        # 🚨 종료 시간 (TIME)
        reservation_date,    # 🚨 날짜 (DATE)
        room_id,             # room_id
        seat_number,         # seat_number
    ):
        raise HTTPException(status_code=409, detail="ALREADY_RESERVED_OVERLAP")
        
    # 6. 최종 예약 생성 (INSERT)
    reservation_data = {
        'sid': sid_found,
        'room_id': room_id,
        'seat_number': seat_number,
        'date': reservation_date,
        'start_time': start_time_str,
        'end_time': end_time_str
    }
    
    success, error_details = create_reservation(reservation_data)
    
    if not success:
        # DB 오류 발생 시
        raise HTTPException(status_code=500, detail=error_details.get('error_code'))
        
    # 7. 성공 응답 반환
    return success_response(
        message="SEAT_RESERVE_SUCCESS", 
        status_code=status.HTTP_201_CREATED
    )

    # # --- 3. 시간 및 상태 검증 (DB X & SELECT) ---
    
    # # 3-A. 시간대 유효성 확인 (DB X - Block 5)
    # # Note: 운영 시간대는 설정 테이블에서 가져와야 하지만, 여기서는 임시 값으로 가정
    # operating_hours = {
    #     "open": seat_info.get('open'),  # get_seat_information의 T2.open 컬럼 값
    #     "close": seat_info.get('close') # get_seat_information의 T2.close 컬럼 값
    # }
    # is_time_valid, error_details = check_time(
    #     data['start_time'], data['end_time'], operating_hours
    # )
    # if not is_time_valid:
    #     raise HTTPException(status_code=409, detail="WRONG_TIME")
        
    # # 3-B. 회원이 정석 내부에 들어온 상태인지 확인 (SELECT - Block 13)
    # if not check_student_inside(sid):
    #     raise HTTPException(status_code=409, detail="WRONG_POSITION_LIBRARY")

    # # 4. 개인 중복 예약 확인 (SELECT)
    # # Note: seat_reservation 테이블에서 해당 sid가 현재 시간 이후에 다른 예약이 있는지 확인
    # if check_time_overlap(
    #     data['start_time'], data['end_time'], sid, table_name='seat_reservation_self_check' # 임시 테이블 명
    # ):
    #     raise HTTPException(status_code=409, detail="ALREADY_RESERVED_SELF")


    # # 5. 타인 예약 충돌 확인 (SELECT - Block 8)
    # # Note: exclude_res_id=None으로 설정하여 모든 기존 예약을 대상으로 검증
    # if check_time_overlap(
    #     data['start_time'], data['end_time'], data['room_id'], table_name='seat_reservation', exclude_res_id=None
    # ):
    #     raise HTTPException(status_code=409, detail="ALREADY_RESERVED_OTHER")


    # # --- 6. 예약 기록 최종 저장 (INSERT) ---
    # # Note: create_reservation 함수는 data 딕셔너리와 type을 받아 최종 INSERT를 실행
    # success, error_details = create_reservation(data, type='seat')
    # if not success:
    #     raise HTTPException(status_code=500, detail="DB_ERROR")
        
    
    # # 7. 성공 응답 반환 (DB X - Block 3)
    # return success_response(
    #     message="SEAT_RESERVE_SUCCESS", 
    #     status_code=201
    # )





# --- 좌석 예약 기록 확인 핸들러 (GET /seat/status) ---
@router.get("/status")
async def get_seat_status_handler(
    room_id: Optional[str] = Query(None), seat_number: Optional[int] = Query(None), sid: Optional[str] = Query(None)
):
    conditions = {'room_id': room_id, 'seat_number': seat_number, 'sid': sid}
    conditions = {k: v for k, v in conditions.items() if v is not None} # None 값 제거
        
    # 1. 조건에 맞는 예약 기록 조회 (SELECT)
    result = get_reservation_status(conditions=conditions)
    
    # 500 DB 실행 오류 확인
    if isinstance(result, tuple) and not result[0]:
        raise HTTPException(status_code=500, detail="DB_ERROR")
        
    # 2. DB Row 객체를 JSON 리스트로 변환 및 반환
    seat_status_list = format_db_rows_to_json(result)

    return success_response(message="SEAT_STATUS_SUCCESS", status_code=200, data=seat_status_list)


# 좌석 예약 반납
@router.post("/return", status_code=status.HTTP_201_CREATED)
async def return_seat_handler(data: Dict[str, Any]):
    """
    [API Handler] sid를 기반으로 현재 활성화된 좌석 예약을 반납(취소) 처리합니다.
    """
    
    # 1. 필수 입력값 확인 (400 방어)
    REQUIRED_KEYS = ['sid']
    validation_result = validate_input(data, REQUIRED_KEYS)
    
    if validation_result is not True:
        _, error_detail = validation_result
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(
                error_code=error_detail['error_code'],
                message=error_detail['message']
            )
        )
    
    sid_to_cancel = data.get('sid')
    
    # 2. 현재 활성화된 예약 기록 조회 (SELECT)
    # sid와 함께, 예약이 '현재 시간' 이후의 예약인지 조건도 함께 전달해야 함.
    conditions = {'sid': sid_to_cancel}
    
    # get_reservation_status는 List[Row]를 반환하므로, 이를 처리해야 합니다.
    result = get_reservation_status(conditions)
    
    # 500 DB 실행 오류 확인
    # if isinstance(result, tuple) and not result[0]:
    #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_response(error_code="DB_ERROR"))
    if isinstance(result, tuple) and not result[0]:
        # result[1]은 error_details 딕셔너리입니다.
        error_details = result[1] 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            # 🚨 수정: error_response에 error_details를 전달
            detail=error_response(
                error_code=error_details.get('error_code', 'DB_ERROR'),
                message=error_details.get('message', '예약 조회 중 DB 오류가 발생했습니다.')
            )
        )


    # 🚨 DB 조회 결과가 리스트이므로, 단일 활성 예약만 확인합니다.
    # 현재 활성화된 예약이 없거나 (빈 리스트), 
    # 여러 개라면 논리 오류지만, 여기서는 [0]만 사용하거나 오류 처리함.
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response(
                error_code="NOT_FOUND",
                message="현재 활성화된 반납/취소할 좌석 예약이 없습니다."
            )
        ) 
        
    # 3. 예약 정보 추출 및 반납 실행 준비
    # 가장 최근의 (혹은 유일한) 활성 예약을 선택하여 딕셔너리로 변환
    # active_reservation = dict(result[0])
    active_reservation = result[0]
    reservation_id = active_reservation['reservation_id']
    
    # 4. 기록 삭제/갱신 실행 (DELETE/UPDATE 트랜잭션 - 500 방어)
    # 'seat'는 DELETE(취소)로 설계되었으므로, 해당 함수를 호출합니다.
    success, error_details = execute_reservation_return(reservation_id) 
    
    # if not success:
    #     # DB 트랜잭션 오류 발생 시
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
    #         detail=error_response(error_code="DB_ERROR", message=error_details.get('message'))
    #     )

    if not success:
        # DB 트랜잭션 오류 발생 시
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=error_response(
                error_code=error_details.get('error_code', 'DB_ERROR'), # 🚨 오류 코드 추출
                message=error_details.get('message', '예약 반납 중 DB 오류가 발생했습니다.')
            )
        )
        
    # 5. 성공 응답 반환 (201 Created)
    return success_response(
        message="SEAT_CANCEL_SUCCESS", 
        status_code=status.HTTP_201_CREATED,
        data={"reservation_id": reservation_id, "action": "Cancelled"}
    )

# 좌석 예약 연장


# --- 좌석 예약 연장 핸들러 (POST /seat/extend) ---
@router.post("/extend", status_code=status.HTTP_201_CREATED)
async def extend_seat_reservation_handler(data: Dict[str, Any]):
    """
    [API Handler] 기존 좌석 예약의 종료 시간을 연장하는 요청을 처리합니다.
    """
    
    # 1. 필수값 유효성 검사 (400 Bad Request 방어)
    # 예약 ID(reservation_id)와 학번(sid) 또는 인증 데이터(face/card)가 필요하다고 가정합니다.
    # 여기서는 간소화를 위해 'reservation_id'와 'sid'를 필수로 가정합니다.
    REQUIRED_KEYS = ['reservation_id', 'sid'] 
    validation_result = validate_input(data, REQUIRED_KEYS)
    
    if validation_result is not True:
        _, error_detail = validation_result
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_response(
                error_code=error_detail['error_code'], 
                message=error_detail['message']
            )
        )
    
    res_id = data.get('reservation_id')
    sid = data.get('sid')
    
    # 2. 예약 기록이 존재하는지 확인 후 조회 (404 Not Found 방어)
    # get_reservation_by_id 함수는 해당 ID의 예약 기록을 조회하고,
    # 해당 sid와 일치하는지 내부적으로 검증한다고 가정합니다.
    # reservation_info = get_reservation_status(res_id, sid)
    
    # if reservation_info is None:
    #     # 예약 ID가 없거나, 해당 sid의 예약이 아닌 경우 (404 처리)
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail=error_response(
    #             error_code="NOT_FOUND",
    #             message=f"예약 ID {res_id}를 찾을 수 없거나, 해당 회원의 예약이 아닙니다."
    #         )
    #     )
        
    # 2. 예약 기록이 존재하는지 확인 후 조회 (404 Not Found 방어)
    conditions = {'reservation_id': res_id, 'sid': sid}
    # get_reservation_status가 List[Dict]를 반환하므로, 이를 받습니다.
    result = get_reservation_status(conditions)

    # DB 오류 확인
    if isinstance(result, tuple) and not result[0]:
        raise HTTPException(status_code=500, detail="DB_ERROR")

    # reservation_info_list가 빈 리스트면 예약이 없는 것 (404)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response(error_code="NOT_FOUND", message=f"예약 ID {res_id}를 찾을 수 없습니다.")
    )
    # 🚨 DB Row 객체를 단일 딕셔너리로 변환 (List[Row] -> Dict)
    # reservation_info = dict(result[0])
    reservation_info = result[0]

    # 🚨 3. 연장 가능성 검증 (새로운 로직)
    # reservation_info_list에는 하나의 예약 정보만 들어있어야 합니다.
    is_valid, error_detail = check_extension_validity(reservation_info)

    if not is_valid:
            # 연장 규칙 위반 시 409 Conflict 반환
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_response(
                    error_code=error_detail['error_code'],
                    message=error_detail['message']
                )
            )
    
    # 4. 기록 변경 (UPDATE 트랜잭션 실행)
    # execute_extend_reservation 함수는 기존 예약의 종료 시간만 업데이트한다고 가정합니다.
    success, error_details = execute_extend_reservation(res_id)
    
    if not success:
        # DB 저장 중 오류 발생 시 (500 Internal Server Error)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                error_code="DB_ERROR",
                message=f"예약 연장 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
            )
        )
        
    # 5. 성공 응답 반환 (201 Created)
    # 연장에 성공하여 DB 상태가 변경되었으므로 201 Created를 반환합니다.
    return success_response(
        message="SEAT_EXTEND_SUCCESS",
        status_code=status.HTTP_201_CREATED,
        data={"reservation_id": res_id}
    )

# seat_api.py 맨 아래에 추가

@router.get("/stats")
async def get_seat_stats_handler():
    """
    [API Handler] 각 열람실별 총 좌석 수와 현재 사용 중인 좌석 수를 반환합니다.
    """
    # 실제로는 DB의 study_room_status 테이블이나 seat_reservation을 조회해야 합니다.
    # 여기서는 예시로 seat_reservation 테이블에서 room_id별 개수를 센다고 가정합니다.
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 각 열람실별 현재 활성화된(return_time이 NULL인) 예약 수 조회
    sql = """
        SELECT room_id, COUNT(*) as used_count 
        FROM seat_reservation 
        WHERE return_time IS NULL 
        GROUP BY room_id
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    
    # 초기 데이터 (총 좌석 수는 고정값이거나 study_room 테이블에서 가져와야 함)
    stats = {
        "1": {"total": 375, "current": 0},       # 제1열람실
        "2-1": {"total": 269, "current": 0},     # 제2-1열람실
        "2-2": {"total": 134, "current": 0},     # 제2-2열람실
        "2-2_grad": {"total": 62, "current": 0}  # 대학원생
    }
    
    for row in rows:
        rid = row['room_id']
        count = row['used_count']
        if rid in stats:
            stats[rid]['current'] = count
            
    return success_response(message="STATS_SUCCESS", status_code=200, data=stats)