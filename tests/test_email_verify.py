from app.services.email_verify import (
    check_disposable,
    check_free_webmail,
    check_role_based,
    check_syntax,
)
from app.services.pattern_inference import generate_candidates
from app.services.risk_score import grade_email
from app.services.email_verify import SMTPCheckResult


def test_syntax_valid():
    assert check_syntax("jane.doe@example.com") is True
    assert check_syntax("not-an-email") is False
    assert check_syntax("missing@domain") is False


def test_disposable_detection():
    assert check_disposable("someone@mailinator.com") is True
    assert check_disposable("someone@example.com") is False


def test_role_based_detection():
    assert check_role_based("support@example.com") is True
    assert check_role_based("jane.doe@example.com") is False


def test_free_webmail_detection():
    assert check_free_webmail("someone@gmail.com") is True
    assert check_free_webmail("someone@acmecorp.com") is False


def test_pattern_generation_basic():
    candidates = generate_candidates("Jane", "Doe", "example.com")
    emails = [c.email for c in candidates]
    assert "jane.doe@example.com" in emails
    assert "jdoe@example.com" in emails
    # highest prior pattern should be first
    assert candidates[0].pattern_name == "first.last"


def test_pattern_generation_handles_accents():
    candidates = generate_candidates("José", "Núñez", "example.com")
    emails = [c.email for c in candidates]
    assert "jose.nunez@example.com" in emails


def test_grade_email_rejected_is_F():
    grade = grade_email(
        syntax_valid=True, is_disposable=False, is_role_based=False,
        is_free_webmail=False, has_mx=True, smtp_result=SMTPCheckResult.REJECTED,
    )
    assert grade == "F"


def test_grade_email_accepted_corporate_is_A():
    grade = grade_email(
        syntax_valid=True, is_disposable=False, is_role_based=False,
        is_free_webmail=False, has_mx=True, smtp_result=SMTPCheckResult.ACCEPTED,
    )
    assert grade == "A"


def test_grade_email_catch_all_is_C():
    grade = grade_email(
        syntax_valid=True, is_disposable=False, is_role_based=False,
        is_free_webmail=False, has_mx=True, smtp_result=SMTPCheckResult.CATCH_ALL,
    )
    assert grade == "C"
