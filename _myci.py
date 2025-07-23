import os
import bg_helper as bh


# Call via the following:
#   tools-py-python ~/repos/personal/packages/redis-helper/_myci.py

this_dir = os.path.dirname(os.path.abspath(__file__))
local_package_paths = [this_dir]
# bg_helper_dir = os.path.join(os.path.dirname(this_dir), 'bg-helper')
# if os.path.isdir(bg_helper_dir):
#     local_package_paths.append(bg_helper_dir)


def create_test_environments():
    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.5.10',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4',
        dep_versions_dict={
            'redis': '3.5.3',
            'hiredis': '1.1.0',
        }
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.6.15',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4, pdbpp==0.10.3',
        dep_versions_dict={
            'redis': '4.3.6, 4.2.1, 3.5.3',
            'hiredis': '2.0.0, 1.1.0',
        }
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.7.17',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4, pdbpp',
        dep_versions_dict={
            'redis': '5.0.8, 4.6.0, 3.5.3',
            'hiredis': '2.3.2, 1.1.0',
        }
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.8.20',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4, pdbpp',
        dep_versions_dict={
            'redis': '6.1.1, 5.3.0, 4.6.0, 3.5.3',
            'hiredis': '3.2.1, 2.4.0, 1.1.0',
        }
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.9.20',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4, pdbpp',
        dep_versions_dict={
            'redis': '6.2.0, 5.3.0, 4.6.0, 3.5.3',
            'hiredis': '3.2.1, 2.4.0, 1.1.0',
        }
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.10.15, 3.11.10',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4, pdbpp',
        dep_versions_dict={
            'redis': '6.2.0, 5.3.0, 4.6.0, 3.5.3',
            'hiredis': '3.2.1, 2.4.0, 1.1.0',
        }
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.12.7, 3.13.5',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4, pdbpp',
        dep_versions_dict={
            'redis': '6.2.0, 5.3.0, 4.6.0, 4.1.0',
            'hiredis': '3.2.1, 2.4.0, 2.1.1',
        }
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.7.17, 3.8.20, 3.9.20, 3.10.15, 3.11.10, 3.12.7, 3.13.5',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4, pdbpp',
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.5.10',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4',
    )

    bh.tools.pyenv_create_venvs_for_py_versions_and_dep_versions(
        this_dir,
        py_versions='3.6.15',
        die=True,
        local_package_paths=local_package_paths,
        extra_packages='pytest<=7.4.4, pdbpp==0.10.3',
    )


if __name__ == '__main__':
    create_test_environments()
