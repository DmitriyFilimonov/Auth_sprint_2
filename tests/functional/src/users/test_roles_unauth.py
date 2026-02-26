from http import HTTPStatus


import pytest


@pytest.mark.parametrize(
    "expected_answer",
    [
        {
            "status": HTTPStatus.UNAUTHORIZED,
        },
    ],
)
@pytest.mark.asyncio
async def test_roles_unauth(make_auth_request, expected_answer: dict):
    response = await make_auth_request("get", "/roles")

    print(response)

    assert response["status"] == expected_answer["status"]
