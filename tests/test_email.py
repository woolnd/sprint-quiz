from sprint_quiz.db.schema import init_db
from sprint_quiz.db.repository import add_subscriber
from sprint_quiz.notify.email import send_daily_email

init_db()

# 본인 이메일을 테스트 구독자로 등록
result = add_subscriber(channel="email", address="wodnd0418@gmail.com")
print(f"구독자 등록: {'성공' if result else '이미 등록됨'}")

send_daily_email()