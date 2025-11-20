import pathlib
import re
import shutil


def main():

    parent_path = pathlib.Path(__file__).resolve().parent

    if (parent_path.is_dir()):
        zip_source_path = pathlib.Path.joinpath(parent_path, "vrage_tools")

        with zip_source_path.joinpath("__init__.py").open() as init_file:
            init_content = init_file.read()
        init_file.close()

        addon_version_match = re.search(r"([\"\']version[\"\']\s*:\s*(\(\s*[0-9]*\,\s*[0-9]*\,\s*[0-9]*\)))", init_content)
        if (addon_version_match is not None):

            addon_version = str(
                re.sub(
                    r"[\(*\)*]|\s*",
                    "",
                    str(
                        re.search(
                            r"(\(\s*[0-9]*\,\s*[0-9]*\,\s*[0-9]*\))",
                            str(addon_version_match)
                        ).group()
                    )
                )
            ).replace(",", ".")

            zip_target_path = parent_path.joinpath(f"Blender_VRAGE_Tools_v{addon_version}")

            shutil.copytree(zip_source_path, parent_path.joinpath("temp", "vrage_tools"))
            temp_folder = parent_path.joinpath("temp")

            zipfile = shutil.make_archive(zip_target_path, "zip", temp_folder)
            shutil.rmtree(temp_folder)
        else:
            raise ValueError(f"Addon version not found Value is: {addon_version_match}")
    else:
        raise ValueError(f"Parent_Path is not is not a directory: {parent_path}")


if __name__ == '__main__':
    main()
