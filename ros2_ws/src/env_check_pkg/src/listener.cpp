#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

class ListenerNode : public rclcpp::Node {
public:
  ListenerNode() : Node("env_check_pkg_listener") {
    subscription_ = this->create_subscription<std_msgs::msg::String>(
        "env_check_chatter", 10,
        [this](const std_msgs::msg::String::SharedPtr msg) { handleMessage(msg); });
    RCLCPP_INFO(this->get_logger(), "AAE5303 listener awaiting messages.");
  }

private:
  void handleMessage(const std_msgs::msg::String::SharedPtr msg) const {
    RCLCPP_INFO(this->get_logger(), "I heard: '%s'", msg->data.c_str());
  }

  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr subscription_;
};

int main(int argc, char *argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<ListenerNode>());
  rclcpp::shutdown();
  return 0;
}

