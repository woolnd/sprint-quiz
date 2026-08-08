from sprint_quiz.generator.quiz import generate_quiz

sample = """
ReLU는 딥러닝에서 널리 쓰이는 활성화 함수다.
"""

result = generate_quiz(sample)
print(result["question"])
print()
print(result["answer"])
print()
print(result["keywords"])