#pragma once

#include <optional>
#include <string>

namespace rapid_inbox::ingestd {

std::optional<std::string> extract_verification_code(const std::string& subject,
                                                     const std::string& sender,
                                                     const std::string& text_body,
                                                     const std::string& html_body,
                                                     const std::string& preview);

}  // namespace rapid_inbox::ingestd
