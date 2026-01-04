from pathlib import Path
from typing import Any, Dict, Optional, Union, List, TextIO
import re


def parse_toon_file(path: Path) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    current_section: Optional[str] = None
    section_data: Optional[Union[Dict[str, Any], List[Any]]] = None

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')

            if ':' in line and not line.strip().startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if not value:
                    if current_section is not None:
                        if section_data is not None:
                            data[current_section] = section_data
                        current_section = key
                        section_data = {}
                    else:
                        data[key] = value
                        current_section = key
                        section_data = {}
                else:
                    if value.startswith('[') and value.endswith(']'):
                        int(value[1:-1])
                        data[key] = []
                        current_section = key
                        section_data = data[key]
                    else:
                        if current_section is not None and section_data is not None:
                            if isinstance(section_data, list):
                                pass
                            elif isinstance(section_data, dict):
                                section_data[key] = parse_value(value)
                        else:
                            data[key] = parse_value(value)

            elif '|' in line and current_section and section_data is not None:
                if isinstance(section_data, list):
                    if '{' in line:
                        headers_match = re.search(r'\{([^}]+)\}', line)
                        if headers_match:
                            headers = [h.strip() for h in headers_match.group(1).split(',')]
                            section_data.append({'headers': headers})
                    else:
                        values = [v.strip() for v in line.split('|')]
                        last_item = section_data[-1] if section_data else {}
                        if 'headers' in last_item:
                            headers = last_item['headers']
                            row = {headers[i]: values[i] if i < len(values) else '' for i in range(len(headers))}
                            section_data.append(row)
                        elif isinstance(last_item, dict):
                            headers = list(last_item.keys())
                            row = {headers[i]: values[i] if i < len(values) else '' for i in range(len(headers))}
                            section_data.append(row)

            elif line.strip().startswith('-'):
                item = line.strip()[1:].strip()
                if current_section and section_data is not None:
                    if isinstance(section_data, list):
                        section_data.append(parse_value(item))
                    elif isinstance(section_data, dict):
                        if current_section not in data:
                            data[current_section] = []
                        if isinstance(data[current_section], list):
                            data[current_section].append(parse_value(item))
                        else:
                            data[current_section] = [parse_value(item)]
                else:
                    if current_section not in data:
                        data[current_section] = []
                    if isinstance(data[current_section], list):
                        data[current_section].append(parse_value(item))

    if current_section is not None and current_section in data:
        pass
    elif current_section is not None and section_data is not None:
        data[current_section] = section_data

    return data


def parse_value(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() == 'true':
        return True
    if value.lower() == 'false':
        return False
    if value.lower() == 'null' or value.lower() == 'none':
        return None
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def write_toon_file(path: Path, data: Dict[str, Any]) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                f.write(f"{key}:\n")
                write_toon_value(f, value, 1)
            else:
                f.write(f"{key}: {format_value(value)}\n")


def write_toon_value(f: TextIO, value: Any, indent: int = 0) -> None:
    prefix = '  ' * indent

    if isinstance(value, dict):
        for k, v in value.items():
            f.write(f"{prefix}- {k}: {format_value(v)}\n")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                write_toon_value(f, item, indent)
            else:
                f.write(f"{prefix}- {format_value(item)}\n")
    else:
        f.write(f"{prefix}- {format_value(value)}\n")


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return 'null'
    return str(value)
