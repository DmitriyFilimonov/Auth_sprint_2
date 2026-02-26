from tests.functional.settings import test_settings
from http import HTTPStatus

import pytest


@pytest.mark.parametrize(
    "expected_answer",
    [
        {
            "status": HTTPStatus.OK,
        },
    ],
)
@pytest.mark.asyncio
async def test_roles_accessed(
    make_auth_request,
    expected_answer: dict,
    clear_auth_db_tables,
    create_super_user,
):
    await clear_auth_db_tables()

    super_user = await create_super_user()

    login_payload = {
        "login": super_user["login"],
        "password": test_settings.auth_db_setting.superuser_password,
    }

    response = await make_auth_request("post", "/login", login_payload)

    headers = {"Authorization": f"Bearer {response["body"]["access_token"]}"}

    response = await make_auth_request("get", "/roles", headers=headers)

    assert response["status"] == expected_answer["status"]
