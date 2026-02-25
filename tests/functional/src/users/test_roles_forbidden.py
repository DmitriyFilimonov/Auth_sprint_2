from http import HTTPStatus

import pytest

from tests.functional.models.user import LoginPayload, UserCreate


user = UserCreate(
    login="admin",
    email="admin@admin.domain",
    first_name="Firstname",
    last_name="Lastname",
    password="passW0RD_LongerThan10",
)

login_payload = LoginPayload(login=user.login, password=user.password)


@pytest.mark.parametrize(
    "expected_answer",
    [
        {
            "status": HTTPStatus.FORBIDDEN,
        },
    ],
)
@pytest.mark.asyncio
async def test_roles_forbidden(
    make_auth_request, expected_answer: dict, clear_auth_db_tables
):
    await clear_auth_db_tables()

    await make_auth_request("post", "/signup", user.dict())

    response = await make_auth_request("post", "/login", login_payload.dict())

    headers = {"Authorization": f"Bearer {response["body"]["access_token"]}"}

    response = await make_auth_request("get", "/roles", headers=headers)

    assert response["status"] == expected_answer["status"]
