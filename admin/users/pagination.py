"""Пагинатор для списков, загруженных с API постранично (уже одна страница в object_list)."""

from django.core.paginator import Paginator


class FilmAPIPaginator(Paginator):
    def __init__(
        self,
        object_list,
        per_page,
        total_count: int,
        orphans=0,
        allow_empty_first_page=True,
    ):
        super().__init__(
            object_list,
            per_page,
            orphans=orphans,
            allow_empty_first_page=allow_empty_first_page,
        )
        self._total_count = total_count

    @property
    def count(self):
        return self._total_count

    def page(self, number):
        number = self.validate_number(number)
        return self._get_page(self.object_list, number, self)
