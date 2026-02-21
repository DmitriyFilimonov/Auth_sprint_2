from http import HTTPStatus

from pydantic import BaseModel

import pytest


class User(BaseModel):
    login: str
    email: str
    first_name: str
    last_name: str
    password: str


@pytest.mark.parametrize(
    "input_data, expected_answer",
    [
        (
            User(
                login="admin",
                email="admin@admin.domain",
                first_name="Firstname",
                last_name="Lastname",
                password="passW0RD_LongerThan10",
            ).dict(),
            {
                "status": HTTPStatus.CREATED,
            },
        ),
    ],
)
@pytest.mark.asyncio
async def test_signup(
    make_auth_request,
    input_data: dict,
    expected_answer: dict,
    clear_auth_db_tables
):
    await clear_auth_db_tables()

    response = await make_auth_request("post", "/signup", input_data)

    print(response)

    assert response["status"] == expected_answer["status"]


# @pytest.mark.parametrize(
#     "query_data, expected_answer",
#     [
#         ({}, {"status": HTTPStatus.OK, "length": 50}),
#         (
#             {"genre": "2fec4f4f-7f84-475c-ad28-791ce135bd2e"},
#             {"status": HTTPStatus.OK, "length": 1},
#         ),
#         (
#             {"genre": "00000000-0000-0000-0000-000000000000"},
#             {"status": HTTPStatus.NOT_FOUND, "length": 1},
#         ),
#         (
#             {"genre": "00000000-0000-0000-0000-0000000000000"},
#             {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "length": 1},
#         ),
#         ({"page": 0}, {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "length": 1}),
#         ({"page": 10000}, {"status": HTTPStatus.NOT_FOUND, "length": 1}),
#         ({"size": 0}, {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "length": 1}),
#         ({"size": 2}, {"status": HTTPStatus.OK, "length": 2}),
#         ({"size": 101}, {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "length": 1}),
#         ({"sort": "random"}, {"status": HTTPStatus.UNPROCESSABLE_ENTITY, "length": 1}),
#     ],
# )
# @pytest.mark.asyncio
# async def test_signup(make_auth_request, query_data: dict, expected_answer: dict):
#     """Тест создания пользователя"""
#     response = await make_auth_request("/signup", "", query_data)

#     assert response["status"] == expected_answer["status"]
#     assert len(response["body"]) == expected_answer["length"]
