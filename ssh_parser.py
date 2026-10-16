
def parse_ssh_config(file_path):
    settings = {}
    warnings = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            # Ignore blank lines and full-line comments
            if not line or line.startswith("#"):
                continue

            # These features need additional parsing logic
            first_word = line.split()[0].lower()

            if first_word in ("include", "match"):
                warnings.append(
                    f"Line {line_number}: "
                    f"{first_word} directive needs extra handling."
                )
                continue

            # Split a directive from its value
            parts = line.split(None, 1)

            if len(parts) != 2:
                warnings.append(
                    f"Line {line_number}: Could not parse directive."
                )
                continue

            key = parts[0].lower()
            value = parts[1].split("#", 1)[0].strip()

            if key in settings:
                warnings.append(
                    f"Line {line_number}: Duplicate directive '{key}'."
                )

            settings[key] = value

    return settings, warnings


if __name__ == "__main__":
    settings, warnings = parse_ssh_config(
        "sample_sshd_config"
    )

    print("Extracted SSH settings:")
    for key, value in settings.items():
        print(f"{key} = {value}")

    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print("-", warning)
