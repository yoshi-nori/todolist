from datetime import datetime
import re


def todomodel_to_dict(todomodel, field_names, **extra_fields):
    """
    __all__を指定する場合はモデルのメソッドはextra_fieldsで指定する必要がある。
    """
    if field_names == "__all__":
        # 自分で設定したフィールドだけ。メソッドは含まれない。
        field_names = [field.name for field in todomodel._meta.get_fields()]
    output = {}
    for field_name in field_names:
        value = getattr(todomodel, field_name)
        if field_name == 'work_date_model':
            value = datetime.strftime(value.work_date, '%m/%d/%Y')
        elif isinstance(value, datetime):
            # value = datetime.strftime(value, '%m/%d/%Y %H:%M:%S%z(%Z)')
            continue
        elif field_name == 'user':
            value = str(value)
        elif callable(value):
            value = value()
        output[field_name] = value
    for key, value in extra_fields.items():
        output[key] = value
    return output

def snake_to_camel(str_snake):
    def convert_string(string):
        return string[1].upper()
    return re.sub("_([a-z0-9])",convert_string, str_snake)

def camel_to_snake(str_camel):
    return re.sub(r"((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))", r"_\1", str_camel).lower()

def convert_dict_key(dic, convert_function):
    def convert_value(value):
        return (
            convert_dict_key(value, convert_function)
            if isinstance(value, dict)
            else [convert_value(elem) for elem in value]
            if isinstance(value, list)
            else value
        )
    return {convert_function(key) : convert_value(value) for key, value in dic.items()}