#pragma once

#include "parsed_mail.h"

#include <stdexcept>
#include <string>

namespace rapid_inbox::ingestd {

class MimeParser {
public:
    ParsedMail parse(const std::string& raw_message) const;
};

std::string decode_base64(const std::string& value);
std::string decode_quoted_printable(const std::string& value);
std::string decode_rfc2047_words(const std::string& value);

}  // namespace rapid_inbox::ingestd
