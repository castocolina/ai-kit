def checked_response(responses, specs, name):
    answers, usage = {}, {"input_tokens": 0, "output_tokens": 0}
    for response in responses:
        if (not isinstance(response, dict) or not isinstance(response.get("model"), str)
                or not response["model"].startswith(BACKENDS[name]["response_prefix"])):
            raise ValueError("invalid_response")
        part, part_usage = response.get("answers"), response.get("usage")
        if not isinstance(part, dict) or set(part) & set(answers):
            raise ValueError("invalid_response")
        if (not isinstance(part_usage, dict)
                or any(type(part_usage.get(k)) is not int or part_usage[k] < 0 for k in usage)):
            raise ValueError("invalid_response")
        answers.update(part)
        for k in usage:
            usage[k] += part_usage[k]
    if set(answers) != set(specs):
        raise ValueError("invalid_response")
    checked = {identifier: _CHECKERS[specs[identifier][0]](answer, specs[identifier][1])
               for identifier, answer in answers.items()}
    return {"model": responses[0]["model"], "answers": checked, "usage": usage}
