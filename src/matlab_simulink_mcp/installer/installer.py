import platform
import subprocess
import sys
import time
from pathlib import Path

system = platform.system()


def find_default_installations() -> list[Path]:
    """Looks for MATLAB in default installation directories."""

    if system == "Windows":
        parent = Path("C:/Program Files/MATLAB")
    elif system == "Linux":
        parent = Path("/usr/local/MATLAB")
    elif system == "Darwin":
        parent = Path("/Applications")
    else:
        raise OSError(f"Unsupported OS: {system}.")

    if not parent.exists():
        return []

    return [p for p in parent.glob("R20[2-9][0-9][ab]*") if p.is_dir()]


def prompt_yes_no(message: str) -> bool:
    """Prompt user with a yes/no/quit question."""
    while True:
        choice = input(f"{message} [Y/N/q]: ").strip().lower()
        if choice in ("y", "yes"):
            return True
        elif choice in ("n", "no"):
            return False
        elif choice == "q":
            raise KeyboardInterrupt
        else:
            print("Invalid choice. Please enter 'Y', 'N', or 'q'.")


def get_setup_path(matlab_root: Path) -> Path | None:
    """Validate if setup.py exists, and then confirm with user"""
    setup_path = matlab_root / "extern" / "engines" / "python" / "setup.py"

    if not setup_path.exists():
        print(f"No MATLAB engine setup found in: {matlab_root}")
    elif prompt_yes_no(f"Install MATLAB engine from {setup_path}?"):
        return setup_path
    return None


def prompt_for_matlab_path() -> Path:
    """Ask user to provide a MATLAB installation path until valid."""
    while True:
        user_input = input("Enter path to MATLAB root directory ('q' to quit): ").strip()
        if not user_input:
            continue
        if user_input.lower() == "q":
            raise KeyboardInterrupt

        matlab_root = Path(user_input)
        if setup_path := get_setup_path(matlab_root):
            return setup_path


def choose_from_installations(installations: list[Path]) -> Path:
    """Let the user pick from multiple MATLAB installations."""
    print("Multiple MATLAB installations found:")
    for i, inst in enumerate(installations, start=1):
        print(f"[{i}] {inst}")

    while True:
        choice = (
            input("Enter number of installation to use, '0' to enter a custom path, or 'q' to quit: ").strip().lower()
        )

        if choice == "q":
            raise KeyboardInterrupt
        if choice == "0":
            return prompt_for_matlab_path()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(installations):
                matlab_root = installations[idx - 1]
                if setup_path := get_setup_path(matlab_root):
                    return setup_path
        else:
            print("Invalid selection.")


def resolve_installation_path() -> Path:
    """Get a confirmed path to MATLAB engine's setup.py"""
    installations = find_default_installations()

    if not installations:
        print("No MATLAB installation found in default directories.")
        return prompt_for_matlab_path()

    if len(installations) == 1:
        matlab_root = installations[0]
        print(f"MATLAB installation found at: {matlab_root}")
        if setup_path := get_setup_path(matlab_root):
            return setup_path
        return prompt_for_matlab_path()

    return choose_from_installations(installations)


def install_engine():
    """Main installation routine for MATLAB Engine."""
    try:
        print("*** MATLAB Engine for Python API Package Installer ***")
        print("This process will install the matlab.engine package from a MATLAB installation on this machine.\n")
        input("Press Enter to continue...")

        setup_dir = resolve_installation_path().parent

        print(f"Installing MATLAB engine from: {setup_dir}")
        print("Requesting permission for installation...")
        time.sleep(2)

        if sys.platform == "win32":
            import ctypes

            from matlab_simulink_mcp.installer import win_elevate

            win_install_log = "install.log"

            script = Path(win_elevate.__file__).resolve()
            status = script.with_name(win_install_log)

            args = subprocess.list2cmdline([str(script), str(setup_dir)])
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, None, 1)
            if ret <= 32:
                raise RuntimeError("Installation failed due to permission issues or some other error.")

            for _ in range(15):
                if status.exists():
                    lines = open(status).read().strip().splitlines()
                    if lines:
                        last = lines[-1]
                        if last == "0":
                            # status.unlink() # had to comment because claude sends request twice in init so it couldnt delete this
                            return
                        elif last.isdigit():
                            e = "\n".join(lines[:-1])
                            # status.unlink()
                            raise RuntimeError(f"Failed to install MATLAB engine. \n: {e}")
                time.sleep(1)
            raise TimeoutError("Installer did not finish in time.")

        else:
            subprocess.run(["sudo", sys.executable, "setup.py", "install"], cwd=setup_dir, check=True)

        time.sleep(2)  # wait for package to be recognized
        input("Installation completed successfully. Press Enter to close...")
        return 0

    except KeyboardInterrupt:
        print("\nAborting installation process...")
        time.sleep(1)
        return 1

    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to close...")
        return 1


if __name__ == "__main__":
    sys.exit(install_engine())
