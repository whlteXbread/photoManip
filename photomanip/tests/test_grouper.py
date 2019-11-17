from nose import tools

from photomanip import PAD, CROP
from photomanip.grouper import FileSystemGrouper


class TestFileSystemGrouper:
    @classmethod
    def setup_class(cls):
        cls.fs_grouper_tag = FileSystemGrouper(
            'photomanip/tests/',
            'faceit365:date='
        )
        cls.fs_grouper = FileSystemGrouper('photomanip/tests/')

    @classmethod
    def teardown_class(cls):
        pass

    def test_daily_grouper(self):
        # test the grouping tag
        day_grouped = self.fs_grouper_tag.group_by_day()
        result_list = list(day_grouped.values())
        tools.eq_(len(result_list), 4)
        tools.eq_(len(result_list[0]), 1)
        tools.eq_(len(result_list[1]), 2)
        tools.eq_(len(result_list[2]), 1)
        tools.eq_(len(result_list[3]), 3)

        # test normal datetime extraction
        day_grouped = self.fs_grouper.group_by_day()
        result_list = list(day_grouped.values())
        tools.eq_(len(result_list), 4)
        tools.eq_(len(result_list[0]), 1)
        tools.eq_(len(result_list[1]), 2)
        tools.eq_(len(result_list[2]), 1)
        tools.eq_(len(result_list[3]), 3)

    def test_monthly_grouper(self):
        # test the grouping tag
        month_grouped = self.fs_grouper_tag.group_by_month()
        result_list = list(month_grouped.values())
        tools.eq_(len(result_list), 2)
        tools.eq_(len(result_list[0]), 3)
        tools.eq_(len(result_list[1]), 4)

        # test normal datetime extraction
        month_grouped = self.fs_grouper.group_by_month()
        result_list = list(month_grouped.values())
        tools.eq_(len(result_list), 2)
        tools.eq_(len(result_list[0]), 3)
        tools.eq_(len(result_list[1]), 4)

    def test_yearly_grouper(self):
        # test the grouping tag
        year_grouped = self.fs_grouper_tag.group_by_year()
        result_list = list(year_grouped.values())
        tools.eq_(len(result_list), 1)
        tools.eq_(len(result_list[0]), 7)

        # test normal datetime extraction
        year_grouped = self.fs_grouper.group_by_year()
        result_list = list(year_grouped.values())
        tools.eq_(len(result_list), 1)
        tools.eq_(len(result_list[0]), 7)

    def test_get_common_dimension(self):
        # test starting with an instance grouped by tag
        day_grouped = self.fs_grouper_tag.group_by_day()

        # test pad
        for _, meta_list in day_grouped.items():
            dim = self.fs_grouper.get_common_dimension(PAD, meta_list)
            tools.eq_(dim, 200)

        # test crop
        dim_list = [136, 138, 150, 132]
        for index, (_, meta_list) in enumerate(day_grouped.items()):
            dim = self.fs_grouper.get_common_dimension(CROP, meta_list)
            tools.eq_(dim, dim_list[index])

        # test starting with an instance _not_ grouped by tag
        day_grouped = self.fs_grouper.group_by_day()

        # test pad
        for _, meta_list in day_grouped.items():
            dim = self.fs_grouper.get_common_dimension(PAD, meta_list)
            tools.eq_(dim, 200)

        # test crop
        dim_list = [136, 138, 150, 132]
        for index, (_, meta_list) in enumerate(day_grouped.items()):
            dim = self.fs_grouper.get_common_dimension(CROP, meta_list)
            tools.eq_(dim, dim_list[index])
