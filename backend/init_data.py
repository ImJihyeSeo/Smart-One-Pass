# init_data.py
# 좌석 정보와 열람실 정보를 입력하는 코드
import psycopg2
from database import get_db_connection

def insert_initial_data():
    """
    중앙 서버 DB에 열람실 정보와 좌석 정보를 대량으로 입력하는 스크립트
    """
    conn = get_db_connection()
    if conn is None:
        print("❌ DB 연결 실패: database.py의 설정을 확인해주세요.")
        return

    try:
        cursor = conn.cursor()
        print("🚀 데이터 삽입을 시작합니다... (중앙 서버로 전송 중)")

        # ==========================================
        # 1. 열람실(study_room) 데이터 정의 및 삽입
        # ==========================================
        # (room_id, room_name, location, open_time, close_time)
        rooms = [
            ("1", "제1열람실", "B1", "06:00:00", "23:59:59"),
            ("2-1", "제2-1열람실", "B1", "06:00:00", "23:59:59"),
            ("2-2", "제2-2열람실", "B1", "06:00:00", "23:59:59"),
            ("2-2_grad", "제2-2열람실(대학원)", "B1", "00:00:00", "23:59:59"),
        ]

        # ON CONFLICT DO NOTHING: 이미 데이터가 있으면 에러 안 내고 무시함 (중복 방지)
        sql_room = """
            INSERT INTO study_room (room_id, room_name, location, open, close)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (room_id) DO NOTHING;
        """
        
        for room in rooms:
            cursor.execute(sql_room, room)
        
        print(f"✅ 열람실 {len(rooms)}개 정보 입력 완료")

        # # ==========================================
        # # 2. 좌석(study_room_seat) 데이터 대량 삽입
        # # ==========================================
        # # 각 열람실별 실제 좌석 수 (프론트엔드 코드 참고함)
        # room_seats_count = {
        #     "1": 376,         # 제1열람실
        #     "2-1": 270,       # 제2-1열람실
        #     "2-2": 136,       # 제2-2열람실
        #     "2-2_grad": 62    # 대학원생실
        # }

        # sql_seat = """
        #     INSERT INTO study_room_seat (room_id, seat_number)
        #     VALUES (%s, %s)
        #     ON CONFLICT (room_id, seat_number) DO NOTHING;
        # """

        # total_inserted = 0
        
        # # 이중 반복문으로 수백 개의 좌석 데이터를 한 번에 생성
        # for room_id, count in room_seats_count.items():
        #     for seat_num in range(1, count + 1):
        #         cursor.execute(sql_seat, (room_id, seat_num))
        #         total_inserted += 1
        
        # print(f"✅ 좌석 정보 총 {total_inserted}개 입력 완료")

        # # ==========================================
        # # 3. 변경 사항 저장 (Commit)
        # # ==========================================
        # conn.commit()
        # print("\n🎉 모든 데이터가 성공적으로 저장되었습니다!")

        # ==========================================
        # 3. [핵심] 복잡한 좌석 번호 생성 로직
        # ==========================================
        
        # 각 열람실별 좌석 리스트를 담을 딕셔너리
        seat_map = {}

        # (1) 제1열람실: 1 ~ 375 (연속)
        seat_map["1"] = list(range(1, 377))

        # (2) 제2-1열람실: 1 ~ 270 (연속)
        seat_map["2-1"] = list(range(1, 271))

        # (3) 제2-2열람실: 띄엄띄엄 구간
        # 1~66, 79~92, 105~120, 137~176
        seats_2_2 = []
        seats_2_2.extend(range(1, 67))    # 1 ~ 66
        seats_2_2.extend(range(79, 93))   # 79 ~ 92
        seats_2_2.extend(range(105, 121)) # 105 ~ 120
        seats_2_2.extend(range(137, 177)) # 137 ~ 176
        seat_map["2-2"] = seats_2_2

        # (4) 대학원실: 띄엄띄엄 구간 + 캐럴(1~6)
        # 67~78, 93~104, 121~136, 177~192
        seats_grad = []
        
        # 일반 좌석 구간
        seats_grad.extend(range(67, 79))   # 67 ~ 78
        seats_grad.extend(range(93, 105))  # 93 ~ 104
        seats_grad.extend(range(121, 137)) # 121 ~ 136
        seats_grad.extend(range(177, 193)) # 177 ~ 192
        
        # 캐럴석 (1~6번으로 저장) -> 다른 좌석 번호(67~)와 안 겹쳐서 OK!
        seats_grad.extend([1, 2, 3, 4, 5, 6]) 
        
        seat_map["2-2_grad"] = seats_grad

        # ==========================================
        # 4. DB에 한 방에 넣기
        # ==========================================
        sql_seat = """
            INSERT INTO study_room_seat (room_id, seat_number)
            VALUES (%s, %s);
        """

        total_count = 0
        for room_id, seat_list in seat_map.items():
            for seat_num in seat_list:
                cursor.execute(sql_seat, (room_id, seat_num))
                total_count += 1
        
        print(f"✅ 좌석 정보 총 {total_count}개 입력 완료")
        print(f"   - 제2-2열람실: {len(seats_2_2)}개")
        print(f"   - 대학원실: {len(seats_grad)}개 (캐럴 6개 포함)")

        # 커밋
        conn.commit()
        print("\n🎉 복잡한 좌석 데이터가 완벽하게 저장되었습니다!")

    except Exception as e:
        conn.rollback() # 에러 나면 취소
        print(f"\n❌ 데이터 삽입 중 오류 발생: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    insert_initial_data()