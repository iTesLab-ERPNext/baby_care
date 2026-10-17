"""Create Nursery Settings and default master data on sites upgraded from 1.0."""


def execute():
    from baby_care.baby_care_management.api.seed import install_master_data

    install_master_data()
