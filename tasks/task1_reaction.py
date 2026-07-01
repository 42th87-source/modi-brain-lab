import time
import random

from config import (
    TRIAL_ORDER_TASK1,
    RANDOM_WAIT_MIN_MS,
    RANDOM_WAIT_MAX_MS,
    PREDICTION_LIMIT_MS,
    DELAY_LIMIT_MS,
    GYRO_ANGULAR_THRESHOLD,
    GYRO_COMPLETE_ANGLE,
    GYRO_RETURN_ANGLE,
    POLL_INTERVAL
)

from data_manager import make_task1_filename, save_task1_rows
from scoring import calculate_task1_summary


def now_ms():
    return time.perf_counter() * 1000


class Task1Reaction:
    def __init__(self, modi_io, participant_id):
        self.modi = modi_io
        self.participant_id = participant_id
        self.rows = []
        self.filename = make_task1_filename(participant_id)

    def show_ready(self, condition):
        print()
        print("==============================")
        print(f"조건: {condition}")
        print("준비하세요.")
        print("==============================")

    def make_invalid_row(self, trial_index, condition, random_wait_ms, early_response, delayed_response, retry_count):
        return {
            "participant_id": self.participant_id,
            "trial_index": trial_index,
            "input_condition": condition,
            "random_wait_ms": random_wait_ms,
            "stimulus_time": "",
            "response_start_time": "",
            "response_complete_time": "",
            "reaction_time_ms": "",
            "completion_time_ms": "",
            "gyro_pitch": "",
            "gyro_roll": "",
            "gyro_angular_velocity": "",
            "early_response": early_response,
            "delayed_response": delayed_response,
            "valid": False,
            "retry_count": retry_count
        }

    def save(self):
        save_task1_rows(self.filename, self.rows)

    def count_valid(self, condition):
        count = 0

        for row in self.rows:
            if row["input_condition"] == condition and row["valid"] is True:
                count += 1

        return count

    def wait_gyro_return(self, start_pitch, start_roll):
        print("자이로를 시작 자세로 돌려놓으세요.")

        while True:
            state = self.modi.get_gyro_state()

            dp = abs(state["pitch"] - start_pitch)
            dr = abs(state["roll"] - start_roll)

            if dp <= GYRO_RETURN_ANGLE and dr <= GYRO_RETURN_ANGLE:
                print("복귀 확인")
                break

            time.sleep(0.05)

    def run_button_trial(self, trial_index, retry_count):
        self.show_ready("button")

        random_wait_ms = random.randint(RANDOM_WAIT_MIN_MS, RANDOM_WAIT_MAX_MS)

        wait_start = now_ms()
        early_response = False

        while now_ms() - wait_start < random_wait_ms:
            if self.modi.is_button_pressed():
                early_response = True
                break

            time.sleep(POLL_INTERVAL)

        if early_response:
            print("조기 반응: 재시행")
            return self.make_invalid_row(
                trial_index,
                "button",
                random_wait_ms,
                True,
                False,
                retry_count
            )

        self.modi.stimulus_on()
        stimulus_time = now_ms()

        response_start_time = None

        while True:
            if self.modi.is_button_pressed():
                response_start_time = now_ms()
                break

            if now_ms() - stimulus_time > 3000:
                response_start_time = now_ms()
                break

            time.sleep(POLL_INTERVAL)

        self.modi.stimulus_off()

        reaction_time_ms = response_start_time - stimulus_time
        delayed_response = reaction_time_ms > DELAY_LIMIT_MS
        valid = reaction_time_ms >= PREDICTION_LIMIT_MS and not delayed_response

        if reaction_time_ms < PREDICTION_LIMIT_MS:
            print(f"{PREDICTION_LIMIT_MS}ms 미만 예측 반응: 재시행")
        elif delayed_response:
            print("1500ms 초과 지연 반응: 기록은 하지만 대표값 제외")
        else:
            print(f"유효 반응: {reaction_time_ms:.1f} ms")

        return {
            "participant_id": self.participant_id,
            "trial_index": trial_index,
            "input_condition": "button",
            "random_wait_ms": random_wait_ms,
            "stimulus_time": stimulus_time,
            "response_start_time": response_start_time,
            "response_complete_time": response_start_time,
            "reaction_time_ms": reaction_time_ms,
            "completion_time_ms": reaction_time_ms,
            "gyro_pitch": "",
            "gyro_roll": "",
            "gyro_angular_velocity": "",
            "early_response": False,
            "delayed_response": delayed_response,
            "valid": valid,
            "retry_count": retry_count
        }

    def run_gyro_trial(self, trial_index, retry_count):
        self.show_ready("gyro")

        start_state = self.modi.get_gyro_state()
        start_pitch = start_state["pitch"]
        start_roll = start_state["roll"]

        random_wait_ms = random.randint(RANDOM_WAIT_MIN_MS, RANDOM_WAIT_MAX_MS)

        wait_start = now_ms()
        early_response = False

        while now_ms() - wait_start < random_wait_ms:
            state = self.modi.get_gyro_state()

            if state["angular_velocity"] >= GYRO_ANGULAR_THRESHOLD:
                early_response = True
                break

            time.sleep(POLL_INTERVAL)

        if early_response:
            print("조기 반응: 재시행")
            return self.make_invalid_row(
                trial_index,
                "gyro",
                random_wait_ms,
                True,
                False,
                retry_count
            )

        self.modi.stimulus_on()
        stimulus_time = now_ms()

        response_start_time = None
        response_complete_time = None

        response_pitch = ""
        response_roll = ""
        response_angular_velocity = ""

        while True:
            state = self.modi.get_gyro_state()

            pitch = state["pitch"]
            roll = state["roll"]
            angular_velocity = state["angular_velocity"]

            if response_start_time is None:
                if angular_velocity >= GYRO_ANGULAR_THRESHOLD:
                    response_start_time = now_ms()
                    response_pitch = pitch
                    response_roll = roll
                    response_angular_velocity = angular_velocity

            if response_start_time is not None:
                dp = abs(pitch - start_pitch)
                dr = abs(roll - start_roll)

                if dp >= GYRO_COMPLETE_ANGLE or dr >= GYRO_COMPLETE_ANGLE:
                    response_complete_time = now_ms()
                    break

            if now_ms() - stimulus_time > 3000:
                if response_start_time is None:
                    response_start_time = now_ms()

                response_complete_time = now_ms()
                break

            time.sleep(POLL_INTERVAL)

        self.modi.stimulus_off()

        reaction_time_ms = response_start_time - stimulus_time
        completion_time_ms = response_complete_time - stimulus_time

        delayed_response = reaction_time_ms > DELAY_LIMIT_MS
        valid = reaction_time_ms >= PREDICTION_LIMIT_MS and not delayed_response

        if reaction_time_ms < PREDICTION_LIMIT_MS:
            print("100ms 미만 예측 반응: 재시행")
        elif delayed_response:
            print("1500ms 초과 지연 반응: 기록은 하지만 대표값 제외")
        else:
            print(f"유효 반응 시작: {reaction_time_ms:.1f} ms")
            print(f"동작 완료: {completion_time_ms:.1f} ms")

        self.wait_gyro_return(start_pitch, start_roll)

        return {
            "participant_id": self.participant_id,
            "trial_index": trial_index,
            "input_condition": "gyro",
            "random_wait_ms": random_wait_ms,
            "stimulus_time": stimulus_time,
            "response_start_time": response_start_time,
            "response_complete_time": response_complete_time,
            "reaction_time_ms": reaction_time_ms,
            "completion_time_ms": completion_time_ms,
            "gyro_pitch": response_pitch,
            "gyro_roll": response_roll,
            "gyro_angular_velocity": response_angular_velocity,
            "early_response": False,
            "delayed_response": delayed_response,
            "valid": valid,
            "retry_count": retry_count
        }

    def run_one_trial_with_retry(self, trial_index, condition):
        retry_count = 0

        while True:
            input(f"{trial_index}번째 시행({condition}) 준비되면 Enter")

            if condition == "button":
                row = self.run_button_trial(trial_index, retry_count)
            else:
                row = self.run_gyro_trial(trial_index, retry_count)

            self.rows.append(row)
            self.save()

            if row["early_response"] is True:
                retry_count += 1
                continue

            if row["reaction_time_ms"] != "":
                if float(row["reaction_time_ms"]) < PREDICTION_LIMIT_MS:
                    retry_count += 1
                    continue

            break

    def run_extra_trials_if_needed(self):
        for condition in ["button", "gyro"]:
            while self.count_valid(condition) < 3:
                trial_index = f"extra_{condition}_{self.count_valid(condition) + 1}"

                print()
                print(f"{condition} 유효 시행이 3회 미만입니다.")
                input("추가 시행 준비되면 Enter")

                retry_count = 0

                if condition == "button":
                    row = self.run_button_trial(trial_index, retry_count)
                else:
                    row = self.run_gyro_trial(trial_index, retry_count)

                self.rows.append(row)
                self.save()

    def print_summary(self):
        summary = calculate_task1_summary(self.rows)

        print()
        print("========== TASK 1 결과 요약 ==========")
        print(f"버튼 유효 시행 수: {summary['button_valid_count']}")
        print(f"자이로 유효 시행 수: {summary['gyro_valid_count']}")

        if summary["button_median"] is not None:
            print(f"버튼 대표값: {summary['button_median']:.1f} ms")

        if summary["gyro_median"] is not None:
            print(f"자이로 대표값: {summary['gyro_median']:.1f} ms")

        if summary["input_difference"] is not None:
            print(f"입력 방식 차이: {summary['input_difference']:.1f} ms")

        print(f"저장 파일: {self.filename}")

    def run(self):
        print()
        print("TASK 1 - 반응속도와 입력 방식")
        print("연습 시행을 시작합니다.")

        input("버튼 연습 준비되면 Enter")
        self.run_button_trial("practice_button", 0)

        input("자이로 연습 준비되면 Enter")
        self.run_gyro_trial("practice_gyro", 0)

        print()
        print("본 시행을 시작합니다.")

        for trial_index, condition in enumerate(TRIAL_ORDER_TASK1, start=1):
            self.run_one_trial_with_retry(trial_index, condition)

        self.run_extra_trials_if_needed()
        self.print_summary()
        self.modi.stimulus_off()