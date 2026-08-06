#不需要代码切片的示例
question_no_need_slice = """审查这段代码:

      def calculate_average(scores):
          total = 0
          for s in scores
              total += s              # 缩进错误（缺少冒号导致语法错误）
          avg = total / len(scores)   # 当scores为空时会抛出ZeroDivisionError
          return avg

      def main():
          data = [85, 92, 78, 90]
          result = calculate_average(data)
          print(f"平均分是：{result}")

          print("最高分是：", max_score)   # NameError

          num = 10
          text = "20"
          sum = num + text              # TypeError

      if __name__ == "__main__":
          main()
  """

question_error_code ="""审查这段代码:
import json
import os

def load_students(file_path, cache=[]):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
        cache.extend(data)  # 每次调用都会累积
    return cache

def calculate_average(scores):
    total = 0
    for s in scores:
        total += s  # 如果s是字符串会出错
    return total / len(scores)

def sort_students(students, key='name'):
    return sorted(students, key=lambda x: x[key])  # 如果key不存在则KeyError

def save_report(report, filename):
    f = open(filename, 'w')
    f.write(report)

# 主要程序
def main():
    students = load_students('students_data.json')
    
    # 手动添加一些学生（模拟数据）
    students.append({'name': 'Alice', 'scores': [95, 88, 92]})
    students.append({'name': 'Bob', 'scores': [78, 82, 79]})
    students.append({'name': 'Charlie', 'scores': [88, 91, 85]})
    students.append({'name': 'David', 'scores': [70, 65, 72]})
    
    # 计算每个学生的平均分并添加
    for student in students:
        avg = calculate_average(student['scores'])  # 这里没问题，但若scores含字符串则出错
        student['avg'] = avg
    
    sorted_students = sort_students(students, key='avg')  # 实际上sort_students默认按name，这里传avg但函数内部未处理
    
    # 生成报告字符串
    report = "Student Report\n"
    report += "=" * 30 + "\n"
    for i, s in enumerate(sorted_students):
        report += f"{i+1}. {s['name']} - Average: " + s['avg'] + "\n"  # s['avg']是float，与str拼接出错
    
    # 保存报告
    save_report(report, 'report.txt')
    
    # 打印报告到控制台
    print(report)
    
    zero_list = []
    avg_zero = calculate_average(zero_list)  # 除零错误
    
    if False:
        unused_var = 10
    print(unused_var)  # NameError

# 入口调用
if __name__ == '__main__':
    main()
"""

question_normal = """审查这段代码:
import json,os
class Student:
    total_students = 0

    def __init__(self, name, student_id):
        self.name = name
        self.student_id = student_id
        self.scores = []
        Student.total_students += 1

    def add_score(self, score):
        if 0 <= score <= 100:
            self.scores.append(score)
            return True
        return False

    def get_average(self):
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)

    def get_grade(self):
        avg = self.get_average()
        if avg >= 90:
            return 'A'
        elif avg >= 80:
            return 'B'
        elif avg >= 70:
            return 'C'
        elif avg >= 60:
            return 'D'
        else:
            return 'F'

    @classmethod
    def get_total_students(cls):
        return cls.total_students

    @staticmethod
    def is_valid_score(score):
        return 0 <= score <= 100

    def __str__(self):
        return f"Student(name={self.name}, id={self.student_id}, scores={self.scores})"
"""

question_normal_short = """审查这段代码:
def count_inversions_bruteforce(arr):
    n = len(arr)
    inversion_count = 0

    # 双重循环遍历所有 i < j 的组合
    for i in range(n):
        for j in range(i + 1, n):
            if arr[i] > arr[j]:
                inversion_count += 1

    return inversion_count
"""

question_hello = "如何用python写个hello world"