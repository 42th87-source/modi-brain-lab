from modi_io import ModiIO
from task_manager import TaskManager


def main():
    print("===================================")
    print("        MODI Brain Lab")
    print("===================================")

    participant_id = input("participant_id 입력: ").strip()

    if participant_id == "":
        print("participant_id가 비어 있습니다. 프로그램을 종료합니다.")
        return

    try:
        modi_io = ModiIO()
    except Exception as e:
        print("MODI 연결 중 오류가 발생했습니다.")
        print(e)
        return

    task_manager = TaskManager(modi_io, participant_id)

    while True:
        print()
        print("실행할 TASK를 선택하세요.")
        print("1. TASK 1 - 반응속도와 입력 방식")
        print("0. 종료")

        choice = input("선택: ").strip()

        if choice == "1":
            try:
                task_manager.run_task1()
            except KeyboardInterrupt:
                print()
                print("TASK 1 실행이 중단되었습니다.")
                modi_io.stimulus_off()
            except Exception as e:
                print("TASK 1 실행 중 오류가 발생했습니다.")
                print(e)
                modi_io.stimulus_off()

        elif choice == "0":
            print("프로그램을 종료합니다.")
            modi_io.stimulus_off()
            break

        else:
            print("잘못된 선택입니다. 다시 입력하세요.")


if __name__ == "__main__":
    main()