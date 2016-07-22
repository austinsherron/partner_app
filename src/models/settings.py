from models import Setting


class SettingModel: 

    @staticmethod
    def quarter():
        setting = Setting.query().get()

        if setting:
            return setting.quarter


    @staticmethod
    def year():
        setting = Setting.query().get()

        if setting:
            return setting.year


    @staticmethod
    def num_labs():
        setting = Setting.query().get()

        if setting:
            return setting.num_labs


    @staticmethod
    def repeat_partners():
        setting = Setting.query().get()

        if setting:
            return setting.repeat_partners


    @staticmethod
    def cross_section_partners():
        setting = Setting.query().get()

        if setting:
            return setting.cross_section_partners

