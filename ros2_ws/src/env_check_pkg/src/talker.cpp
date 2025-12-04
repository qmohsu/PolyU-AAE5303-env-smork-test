#include <chrono>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"

using namespace std::chrono_literals;

class TalkerNode : public rclcpp::Node {
public:
  TalkerNode() : Node("env_check_pkg_talker"), counter_(0) {
    publisher_ = this->create_publisher<std_msgs::msg::String>("env_check_chatter", 10);
    timer_ = this->create_wall_timer(500ms, std::bind(&TalkerNode::onTimer, this));
    RCLCPP_INFO(this->get_logger(), "AAE5303 talker ready (publishing at 2 Hz).");
  }

private:
  void onTimer() {
    auto message = std_msgs::msg::String();
    message.data = "AAE5303 hello #" + std::to_string(counter_++);
    publisher_->publish(message);
    RCLCPP_INFO(this->get_logger(), "Publishing: '%s'", message.data.c_str());
  }

  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  std::size_t counter_;
};

int main(int argc, char *argv[]) {
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<TalkerNode>());
  rclcpp::shutdown();
  return 0;
}

