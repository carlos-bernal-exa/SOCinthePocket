from app_extensions.eligibility import is_fact_or_profile
def test_it(): assert is_fact_or_profile({'rule_name':'Fact-XYZ'})
