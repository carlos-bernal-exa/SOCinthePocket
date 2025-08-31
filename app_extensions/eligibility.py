def is_fact_or_profile(rule):
    return (rule.get('rule_name','').lower().startswith(('fact','prof')))
