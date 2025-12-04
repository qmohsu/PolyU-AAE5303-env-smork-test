from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription(
        [
            Node(
                package="env_check_pkg",
                executable="talker",
                name="env_check_pkg_talker",
                output="screen",
            ),
            Node(
                package="env_check_pkg",
                executable="listener",
                name="env_check_pkg_listener",
                output="screen",
            ),
        ]
    )

