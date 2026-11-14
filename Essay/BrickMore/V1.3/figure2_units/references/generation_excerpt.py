def generate(job, revision):
    p = plan(job["category"], job["family"],
             job["instance"], revision)
    ...
    for attempt in range(1, 21):
        co, la, pa, cl, e = build(p, scale)
        v = validate(p, co, la, pa, e)
        ...
        if v["passed"]:
            return (p, co, la, pa, cl, e, v,
                    history, initial)
