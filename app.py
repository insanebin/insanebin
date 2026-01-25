#!/usr/bin/env python3
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List

DATA_PATH = Path(__file__).with_name("data.json")


@dataclass
class Diagnosis:
    code: str
    name: str


@dataclass
class Exercise:
    id: int
    title: str
    description: str


@dataclass
class Patient:
    id: str
    name: str
    active: bool
    start_date: str
    end_date: str
    diagnosis_codes: List[str]


@dataclass
class AppData:
    diagnoses: List[Diagnosis]
    exercises: List[Exercise]
    patients: List[Patient]
    diagnosis_exercise_map: Dict[str, List[int]]

    @classmethod
    def load(cls) -> "AppData":
        payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        return cls(
            diagnoses=[Diagnosis(**item) for item in payload["diagnoses"]],
            exercises=[Exercise(**item) for item in payload["exercises"]],
            patients=[Patient(**item) for item in payload["patients"]],
            diagnosis_exercise_map=payload["diagnosis_exercise_map"],
        )

    def save(self) -> None:
        payload = {
            "diagnoses": [asdict(item) for item in self.diagnoses],
            "exercises": [asdict(item) for item in self.exercises],
            "patients": [asdict(item) for item in self.patients],
            "diagnosis_exercise_map": self.diagnosis_exercise_map,
        }
        DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class AdminConsole:
    def __init__(self, data: AppData) -> None:
        self.data = data

    def run(self) -> None:
        while True:
            print("\n[관리자 메뉴]")
            print("1) 진단명-운동 매칭 조회")
            print("2) 진단명별 매칭 수정")
            print("3) 운동별 매칭 조회")
            print("0) 종료")
            choice = input("선택: ").strip()
            if choice == "1":
                self.show_diagnosis_mappings()
            elif choice == "2":
                self.edit_diagnosis_mapping()
            elif choice == "3":
                self.show_exercise_mappings()
            elif choice == "0":
                break
            else:
                print("올바른 번호를 입력하세요.")

    def show_diagnosis_mappings(self) -> None:
        print("\n[진단명 -> 운동 매칭]")
        for diagnosis in self.data.diagnoses:
            exercise_ids = self.data.diagnosis_exercise_map.get(diagnosis.code, [])
            exercise_titles = [self._exercise_title(eid) for eid in exercise_ids]
            print(f"- {diagnosis.code} {diagnosis.name}: {', '.join(exercise_titles) or '없음'}")

    def edit_diagnosis_mapping(self) -> None:
        code = input("수정할 진단코드 입력: ").strip()
        if code not in {d.code for d in self.data.diagnoses}:
            print("존재하지 않는 진단코드입니다.")
            return
        print("현재 매칭:")
        current_ids = self.data.diagnosis_exercise_map.get(code, [])
        print(", ".join(self._exercise_title(eid) for eid in current_ids) or "없음")
        print("운동 목록:")
        for exercise in self.data.exercises:
            print(f"  {exercise.id}) {exercise.title}")
        raw = input("매칭할 운동 번호를 쉼표로 입력 (예: 1,3): ").strip()
        if not raw:
            print("입력이 없어 변경하지 않습니다.")
            return
        try:
            new_ids = sorted({int(value.strip()) for value in raw.split(",")})
        except ValueError:
            print("숫자만 입력하세요.")
            return
        valid_ids = {exercise.id for exercise in self.data.exercises}
        if not set(new_ids).issubset(valid_ids):
            print("운동 번호가 올바르지 않습니다.")
            return
        self.data.diagnosis_exercise_map[code] = new_ids
        self.data.save()
        print("매칭이 업데이트되었습니다.")

    def show_exercise_mappings(self) -> None:
        print("\n[운동 -> 진단명 매칭]")
        reverse_map: Dict[int, List[str]] = {exercise.id: [] for exercise in self.data.exercises}
        for code, exercise_ids in self.data.diagnosis_exercise_map.items():
            for exercise_id in exercise_ids:
                reverse_map.setdefault(exercise_id, []).append(code)
        for exercise in self.data.exercises:
            codes = reverse_map.get(exercise.id, [])
            diagnoses = [self._diagnosis_label(code) for code in codes]
            print(f"- {exercise.id} {exercise.title}: {', '.join(diagnoses) or '없음'}")

    def _exercise_title(self, exercise_id: int) -> str:
        for exercise in self.data.exercises:
            if exercise.id == exercise_id:
                return exercise.title
        return f"운동 {exercise_id}"

    def _diagnosis_label(self, code: str) -> str:
        for diagnosis in self.data.diagnoses:
            if diagnosis.code == code:
                return f"{diagnosis.code} {diagnosis.name}"
        return code


class PatientConsole:
    def __init__(self, data: AppData) -> None:
        self.data = data

    def run(self) -> None:
        patient_id = input("환자 ID 입력: ").strip()
        patient = next((item for item in self.data.patients if item.id == patient_id), None)
        if not patient:
            print("환자를 찾을 수 없습니다.")
            return
        if not patient.active:
            print("비활성화된 계정입니다.")
            return
        print(f"\n{patient.name}님, 가능한 운동 목록입니다:")
        exercise_ids = self._exercise_ids_for_patient(patient)
        for exercise_id in exercise_ids:
            exercise = self._exercise_by_id(exercise_id)
            if exercise:
                print(f"- {exercise.id} {exercise.title}: {exercise.description}")

    def _exercise_ids_for_patient(self, patient: Patient) -> List[int]:
        ids: List[int] = []
        for code in patient.diagnosis_codes:
            ids.extend(self.data.diagnosis_exercise_map.get(code, []))
        return sorted(set(ids))

    def _exercise_by_id(self, exercise_id: int) -> Exercise | None:
        return next((item for item in self.data.exercises if item.id == exercise_id), None)


def run_demo_tests() -> None:
    data = AppData.load()
    expected_map = {
        "M511": [1, 4],
        "M501": [2],
        "M111": [3, 5],
    }
    assert data.diagnosis_exercise_map == expected_map, "초기 매칭이 요구사항과 다릅니다."
    patient = data.patients[0]
    ids: List[int] = []
    for code in patient.diagnosis_codes:
        ids.extend(data.diagnosis_exercise_map.get(code, []))
    assert sorted(set(ids)) == [1, 4], "환자 진단에 맞는 운동이 올바르지 않습니다."
    print("데모 테스트 통과")


def main() -> None:
    print("재활 운동 영상 테스트 앱")
    print("1) 관리자")
    print("2) 환자")
    print("3) 데모 테스트 실행")
    choice = input("선택: ").strip()
    data = AppData.load()
    if choice == "1":
        AdminConsole(data).run()
    elif choice == "2":
        PatientConsole(data).run()
    elif choice == "3":
        run_demo_tests()
    else:
        print("올바른 번호를 입력하세요.")


if __name__ == "__main__":
    main()
