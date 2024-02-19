#!/usr/bin/python
class FilterModule(object):
    def filters(self):
        return {
            'rclone_translate_arch': self.rclone_translate_arch,
        }

    @staticmethod
    def rclone_translate_arch(ansible_arch):
        rclone_arch_mapping = {
            "x86_64": "amd64",
            "aarch64": "arm"
        }

        return rclone_arch_mapping[ansible_arch]
