from fastapi import APIRouter, HTTPException, Query, status
from typing import Dict, Any, Optional
from ..services.core_service import check_student_exists, create_reservation, check_time, get_seat_information, check_time_overlap, get_reservation_status, check_extension_validity, execute_extend_reservation, execute_reservation_return, get_room_operating_hours
from ..utils.helper_functions import error_response, success_response, format_db_rows_to_json, validate_input
from datetime import datetime, timedelta, timezone
from database import get_db_connection

router = APIRouter()


# 1. 좌석 예약
@router.post("/reserve")
async def reserve_seat_handler(data: Dict[str, Any]):
    
    required_keys = ['sid', 'room_id', 'seat_number']
    if not validate_input(data, required_keys): 
        raise HTTPException(status_code=400, detail="EMPTY_DATA")
        
    sid_found = data.get('sid')
    room_id = data.get('room_id')
    seat_number = data.get('seat_number')

    print(f"[예약 요청 도착] SID: {sid_found}, Room: {room_id}, Seat: {seat_number}")
    
    if sid_found is None:
        raise HTTPException(status_code=400, detail="SID_CANNOT_BE_NULL")
    
    if not check_student_exists(sid_found): 
        print(f"❌ [Debug] 학생을 찾을 수 없음: {sid_found}")
        raise HTTPException(
            status_code=404, 
            detail=error_response(
                error_code="USER_NOT_FOUND", 
                message=f"학번 {sid_found}는 등록되지 않은 회원입니다."
            )
        )

    # 이 학생(sid)으로 예약된 기록을 다 가져옵니다.
    print(f"[검사 시작] 학번 {sid_found}의 기존 예약 기록 조회")
    user_reservations = get_reservation_status(conditions={'sid': sid_found})

    # DB에서 가져온 기록을 터미널에 통째로 출력해봅니다.
    print(f"[DB 조회 결과] 가져온 기록 개수: {len(user_reservations) if user_reservations else 0}개")
    print(f"[상세 내용] {user_reservations}")

    if isinstance(user_reservations, tuple) and not user_reservations[0]:
        raise HTTPException(status_code=500, detail="DB_ERROR_CHECKING_USER")

    active_seat = None
    if user_reservations:
        for res in user_reservations:
            print(f"   -> 검사 중: 좌석 {res.get('seat_number')}번, 반납시간: {res.get('return_time')}")

            if res.get('return_time') is None: 
                active_seat = res
                break
    
    if active_seat:
        print(f"❌ 중복 예약 차단: {sid_found}는 이미 {active_seat.get('seat_number')}번 사용 중")
        raise HTTPException(
            status_code=409,
            detail=error_response(
                error_code="ALREADY_HAS_SEAT",
                message=f"이미 좌석({active_seat.get('seat_number')}번)을 이용 중입니다. 반납 후 다시 시도해주세요."
            )
        )
    else:
        print("✅ 현재 이용 중인 좌석 없음.")
    
    # 예약하려는 좌석의 존재 여부 확인
    result = get_seat_information(room_id, seat_number)
    
    if isinstance(result, tuple):
        print(f"❌ [Debug] 좌석을 찾을 수 없음! Room: '{room_id}', Seat: '{seat_number}'")
        error_details = result[1]
        error_code = error_details.get('error_code')
        
        if error_code in ["DB_CONNECTION_ERROR", "DB_EXECUTION_ERROR"]:
            raise HTTPException(status_code=500, detail=error_code)
            
        raise HTTPException(status_code=404, detail="SEAT_NOT_FOUND")

    KST = timezone(timedelta(hours=9)) 
    now_kst = datetime.now(KST)

    reservation_date = now_kst.strftime('%Y-%m-%d')
    
    FULL_FORMAT = '%Y-%m-%d %H:%M:%S'
    start_time_str = now_kst.strftime(FULL_FORMAT)

    end_time_dt = now_kst + timedelta(hours=3)

    end_time_str = end_time_dt.strftime(FULL_FORMAT)

    # 운영 시간 및 예약 가능 시간 검증
    operating_hours = get_room_operating_hours(room_id)
    
    if operating_hours is None:
        print(f"❌ [Debug] 운영 시간 정보 없음 (Room ID: {room_id})")
        raise HTTPException(status_code=404, detail="ROOM_NOT_FOUND")
    
    print(f"[운영 시간] {operating_hours}")
    print(f"[예약 요청 시간] {start_time_str} ~ {end_time_str}")

    success, error_details = check_time(now_kst.strftime('%H:%M:%S'), end_time_dt.strftime('%H:%M:%S'), operating_hours)

    if not success:
        error_code = error_details.get('error_code')
        print(f"❌ [시간 검증 실패] {error_code}")
        raise HTTPException(status_code=409, detail=error_code)
        
    # 시간 충돌 검사 (check_time_overlap)
    is_overlap = check_time_overlap(
        start_time_str,
        end_time_str,
        reservation_date,
        room_id,
        seat_number,
    )
    
    if is_overlap:
        print(f"❌ [중복 예약 감지]")
        raise HTTPException(status_code=409, detail="ALREADY_RESERVED_OVERLAP")
    
    # 최종 예약 생성
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
        raise HTTPException(status_code=500, detail=error_details.get('error_code'))
        
    return success_response(
        message="SEAT_RESERVE_SUCCESS", 
        status_code=status.HTTP_201_CREATED
    )



# 2. 좌석 예약 기록 확인
@router.get("/status")
async def get_seat_status_handler(
    room_id: Optional[str] = Query(None), seat_number: Optional[int] = Query(None), sid: Optional[str] = Query(None)
):
    conditions = {'room_id': room_id, 'seat_number': seat_number, 'sid': sid}
    conditions = {k: v for k, v in conditions.items() if v is not None}
        
    # 조건에 맞는 예약 기록 조회 (SELECT)
    result = get_reservation_status(conditions=conditions)
    
    if isinstance(result, tuple) and not result[0]:
        raise HTTPException(status_code=500, detail="DB_ERROR")
        
    # DB Row 객체를 JSON 리스트로 변환 및 반환
    seat_status_list = format_db_rows_to_json(result)

    return success_response(message="SEAT_STATUS_SUCCESS", status_code=200, data=seat_status_list)


# 3. 좌석 예약 반납
@router.post("/return", status_code=status.HTTP_201_CREATED)
async def return_seat_handler(data: Dict[str, Any]):
    """
    [API Handler] sid를 기반으로 현재 활성화된 좌석 예약을 반납(취소) 처리합니다.
    """
    
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
    
    # 현재 활성화된 예약 기록 조회
    # sid와 함께, 예약이 '현재 시간' 이후의 예약인지 조건도 함께 전달
    conditions = {'sid': sid_to_cancel}
    
    result = get_reservation_status(conditions)
    
    if isinstance(result, tuple) and not result[0]:
        error_details = result[1] 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=error_response(
                error_code=error_details.get('error_code', 'DB_ERROR'),
                message=error_details.get('message', '예약 조회 중 DB 오류가 발생했습니다.')
            )
        )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response(
                error_code="NOT_FOUND",
                message="현재 활성화된 반납/취소할 좌석 예약이 없습니다."
            )
        ) 
        
    # 예약 정보 추출 및 반납 실행 준비
    active_reservation = result[0]
    reservation_id = active_reservation['reservation_id']
    
    # 기록 삭제/갱신 실행
    success, error_details = execute_reservation_return(reservation_id) 
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=error_response(
                error_code=error_details.get('error_code', 'DB_ERROR'), # 🚨 오류 코드 추출
                message=error_details.get('message', '예약 반납 중 DB 오류가 발생했습니다.')
            )
        )
        
    return success_response(
        message="SEAT_CANCEL_SUCCESS", 
        status_code=status.HTTP_201_CREATED,
        data={"reservation_id": reservation_id, "action": "Cancelled"}
    )




# 4. 좌석 예약 연장 핸들러
@router.post("/extend", status_code=status.HTTP_201_CREATED)
async def extend_seat_reservation_handler(data: Dict[str, Any]):
    """
    [API Handler] 기존 좌석 예약의 종료 시간을 연장하는 요청을 처리합니다.
    """
    
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
        
    # 예약 기록이 존재하는지 확인 후 조회
    conditions = {'reservation_id': res_id, 'sid': sid}
    result = get_reservation_status(conditions)

    # DB 오류 확인
    if isinstance(result, tuple) and not result[0]:
        raise HTTPException(status_code=500, detail="DB_ERROR")

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_response(error_code="NOT_FOUND", message=f"예약 ID {res_id}를 찾을 수 없습니다.")
    )
    reservation_info = result[0]

    # 연장 가능성 검증
    is_valid, error_detail = check_extension_validity(reservation_info)

    if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_response(
                    error_code=error_detail['error_code'],
                    message=error_detail['message']
                )
            )
    
    # 기록 변경
    success, error_details = execute_extend_reservation(res_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_response(
                error_code="DB_ERROR",
                message=f"예약 연장 중 내부 데이터베이스 오류가 발생했습니다. 상세: {error_details.get('message', '알 수 없음')}"
            )
        )
        
    return success_response(
        message="SEAT_EXTEND_SUCCESS",
        status_code=status.HTTP_201_CREATED,
        data={"reservation_id": res_id}
    )


# 5. 현재 좌석 상태
@router.get("/stats")
async def get_seat_stats_handler():
    """
    [API Handler] 각 열람실별 총 좌석 수와 현재 사용 중인 좌석 수를 반환합니다.
    """
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 각 열람실별 현재 활성화된 예약 수 조회
    sql = """
        SELECT room_id, COUNT(*) as used_count 
        FROM seat_reservation 
        WHERE return_time IS NULL 
        GROUP BY room_id
    """
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    
    stats = {
        "1": {"total": 379, "current": 0},       # 제1열람실
        "2-1": {"total": 270, "current": 0},     # 제2-1열람실
        "2-2": {"total": 136, "current": 0},     # 제2-2열람실
        "2-2_grad": {"total": 62, "current": 0}  # 대학원생
    }
    
    for row in rows:
        rid = row['room_id']
        count = row['used_count']
        if rid in stats:
            stats[rid]['current'] = count
            
    return success_response(message="STATS_SUCCESS", status_code=200, data=stats)