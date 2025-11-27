# init_data.py
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

        # ==========================================
        # 2. 좌석(study_room_seat) 데이터 대량 삽입
        # ==========================================
        # 각 열람실별 실제 좌석 수 (프론트엔드 코드 참고함)
        room_seats_count = {
            "1": 375,         # 제1열람실
            "2-1": 269,       # 제2-1열람실
            "2-2": 134,       # 제2-2열람실
            "2-2_grad": 62    # 대학원생실
        }

        sql_seat = """
            INSERT INTO study_room_seat (room_id, seat_number)
            VALUES (%s, %s)
            ON CONFLICT (room_id, seat_number) DO NOTHING;
        """

        total_inserted = 0
        
        # 이중 반복문으로 수백 개의 좌석 데이터를 한 번에 생성
        for room_id, count in room_seats_count.items():
            for seat_num in range(1, count + 1):
                cursor.execute(sql_seat, (room_id, seat_num))
                total_inserted += 1
        
        print(f"✅ 좌석 정보 총 {total_inserted}개 입력 완료")

        # ==========================================
        # 3. 변경 사항 저장 (Commit)
        # ==========================================
        conn.commit()
        print("\n🎉 모든 데이터가 성공적으로 저장되었습니다!")

    except Exception as e:
        conn.rollback() # 에러 나면 취소
        print(f"\n❌ 데이터 삽입 중 오류 발생: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    insert_initial_data()