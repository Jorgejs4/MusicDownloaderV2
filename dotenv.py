import os


def load_dotenv(dotenv_path=None, override=False, encoding="utf-8"):
    """Carga un archivo .env básico sin depender de python-dotenv."""
    if dotenv_path is None:
        dotenv_path = os.path.join(os.getcwd(), ".env")

    if not os.path.exists(dotenv_path):
        return False

    try:
        with open(dotenv_path, "r", encoding=encoding) as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("export "):
                    line = line[7:].strip()
                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if not key:
                    continue

                if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]

                if override or key not in os.environ:
                    os.environ[key] = value
        return True
    except OSError:
        return False
