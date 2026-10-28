import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


def compile_if_cpp(source_path: Path, work_dir: Path) -> list[str]:
    if source_path.suffix == ".cpp":
        exe_path = work_dir / ("sol.exe" if Path.cwd().drive else "sol.out")
        cmd = ["g++", "-O2", "-std=c++20", str(source_path), "-o", str(exe_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            raise RuntimeError(f"Compilation Error in {source_path.name}:\n{res.stderr}")
        return [str(exe_path)]
    elif source_path.suffix == ".py":
        return ["python", str(source_path)]
    raise ValueError(f"Unsupported file extension: {source_path.suffix}. Use .cpp or .py")


def execute_cmd(cmd: list[str], stdin_data: str, timeout_sec: float = 2.0) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "verdict": "OK" if proc.returncode == 0 else "RTE",
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "time_ms": elapsed_ms,
        }
    except subprocess.TimeoutExpired:
        return {"verdict": "TLE", "stdout": "", "stderr": "Time Limit Exceeded", "time_ms": timeout_sec * 1000}


def run_samples(source_file: str, samples: list[dict[str, str]]) -> dict[str, Any]:
    src = Path(source_file).resolve()
    if not src.exists():
        raise FileNotFoundError(f"File not found: {src}")

    with tempfile.TemporaryDirectory() as tmp:
        cmd = compile_if_cpp(src, Path(tmp))
        results = []
        all_passed = True

        for idx, sample in enumerate(samples, start=1):
            run_res = execute_cmd(cmd, sample["input"])
            expected = sample["output"].strip()
            actual = run_res["stdout"]
            passed = (run_res["verdict"] == "OK") and (actual == expected)
            if not passed:
                all_passed = False

            results.append({
                "test_case": idx,
                "status": "PASSED" if passed else (run_res["verdict"] if run_res["verdict"] != "OK" else "WA"),
                "time_ms": run_res["time_ms"],
                "input": sample["input"],
                "expected_output": expected,
                "actual_output": actual,
            })

        return {"all_passed": all_passed, "results": results}


def run_stress_test(
    optimal_file: str,
    brute_file: str,
    generator_file: str,
    iterations: int = 100,
) -> dict[str, Any]:
    opt_path = Path(optimal_file).resolve()
    brute_path = Path(brute_file).resolve()
    gen_path = Path(generator_file).resolve()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        opt_cmd = compile_if_cpp(opt_path, tmp_dir / "opt") if opt_path.suffix == ".cpp" else ["python", str(opt_path)]
        if opt_path.suffix == ".cpp":
            (tmp_dir / "opt").mkdir(exist_ok=True)
            opt_cmd = compile_if_cpp(opt_path, tmp_dir / "opt")

        if brute_path.suffix == ".cpp":
            (tmp_dir / "brute").mkdir(exist_ok=True)
            brute_cmd = compile_if_cpp(brute_path, tmp_dir / "brute")
        else:
            brute_cmd = ["python", str(brute_path)]

        gen_cmd = ["python", str(gen_path)]

        for i in range(1, min(iterations, 500) + 1):
            gen_res = execute_cmd(gen_cmd, str(i))
            if gen_res["verdict"] != "OK":
                raise RuntimeError(f"Generator crashed on iteration {i}: {gen_res['stderr']}")

            test_input = gen_res["stdout"]
            opt_res = execute_cmd(opt_cmd, test_input)
            brute_res = execute_cmd(brute_cmd, test_input)

            if opt_res["verdict"] != "OK" or opt_res["stdout"] != brute_res["stdout"]:
                return {
                    "found_counterexample": True,
                    "iteration": i,
                    "failing_input": test_input,
                    "expected_brute_output": brute_res["stdout"],
                    "actual_optimal_output": opt_res["stdout"],
                    "optimal_verdict": opt_res["verdict"],
                }

        return {"found_counterexample": False, "iterations_tested": iterations}