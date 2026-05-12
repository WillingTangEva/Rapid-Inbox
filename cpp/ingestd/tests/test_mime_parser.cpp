#include "../src/mime_parser.h"

#include <string>

namespace test {
void check(bool condition, const std::string& message);
}

namespace {

using rapid_inbox::ingestd::MimeParser;
using rapid_inbox::ingestd::ParseFailure;

rapid_inbox::ingestd::ParsedMail parse(const std::string& raw_message) {
    return MimeParser().parse(raw_message);
}

}  // namespace

void test_mime_parser_text_only_message() {
    const auto parsed = parse(
        "From: QA Sender <sender@example.com>\r\n"
        "To: foo@adb.com\r\n"
        "Subject: Hello Rapid Inbox\r\n"
        "Message-ID: <hello@example.com>\r\n"
        "Date: Wed, 13 May 2026 10:00:00 +0000\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "Hello from C++ parser.\r\n"
        "Second line.\r\n");

    test::check(parsed.subject.value_or("") == "Hello Rapid Inbox", "subject decoded");
    test::check(parsed.from_addr.value_or("") == "sender@example.com", "from addr");
    test::check(parsed.text_body.find("Hello from C++ parser.") != std::string::npos, "text body");
    test::check(parsed.text_preview.value_or("").find("Hello from C++ parser.") == 0,
                "preview");
    test::check(parsed.headers_json.find("[[\"From\"") != std::string::npos, "headers json");
}

void test_mime_parser_html_only_message() {
    const auto parsed = parse(
        "From: QA Sender <sender@example.com>\r\n"
        "To: foo@adb.com\r\n"
        "Subject: Hello HTML\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "\r\n"
        "<html><body><p>Hello <strong>Rapid Inbox</strong>.</p><p>Second line</p></body></html>\r\n");

    test::check(parsed.html_body.find("<strong>Rapid Inbox</strong>") != std::string::npos,
                "html body");
    test::check(parsed.text_preview.value_or("") == "Hello Rapid Inbox. Second line",
                "html preview");
}

void test_mime_parser_multipart_alternative() {
    const auto parsed = parse(
        "From: QA Sender <sender@example.com>\r\n"
        "To: foo@adb.com\r\n"
        "Subject: Alternative\r\n"
        "MIME-Version: 1.0\r\n"
        "Content-Type: multipart/alternative; boundary=\"alt-boundary\"\r\n"
        "\r\n"
        "--alt-boundary\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "Plain body from alternative.\r\n"
        "\r\n"
        "--alt-boundary\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "\r\n"
        "<html><body><p>Plain body from alternative.</p><p><strong>HTML</strong> body.</p></body></html>\r\n"
        "\r\n"
        "--alt-boundary--\r\n");

    test::check(parsed.text_body.find("Plain body from alternative.") != std::string::npos,
                "text body");
    test::check(parsed.html_body.find("<strong>HTML</strong> body.") != std::string::npos,
                "html body");
}

void test_mime_parser_attachment_base64() {
    const auto parsed = parse(
        "From: QA Sender <sender@example.com>\r\n"
        "To: foo@adb.com\r\n"
        "Subject: Attachment\r\n"
        "MIME-Version: 1.0\r\n"
        "Content-Type: multipart/mixed; boundary=\"mixed-boundary\"\r\n"
        "\r\n"
        "--mixed-boundary\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "This message has an attachment.\r\n"
        "\r\n"
        "--mixed-boundary\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "Content-Disposition: attachment; filename=\"report.txt\"\r\n"
        "Content-Transfer-Encoding: base64\r\n"
        "\r\n"
        "UXVhcnRlcmx5IHJlcG9ydAo=\r\n"
        "\r\n"
        "--mixed-boundary--\r\n");

    test::check(parsed.attachments.size() == 1, "one attachment");
    test::check(parsed.attachments[0].filename.value_or("") == "report.txt",
                "attachment filename");
    test::check(parsed.attachments[0].content == "Quarterly report\n", "attachment content");
    test::check(parsed.attachments[0].content_type == "text/plain", "attachment content type");
}

void test_mime_parser_inline_related_part() {
    const auto parsed = parse(
        "From: QA Sender <sender@example.com>\r\n"
        "To: foo@adb.com\r\n"
        "Subject: Inline\r\n"
        "MIME-Version: 1.0\r\n"
        "Content-Type: multipart/related; boundary=\"related-boundary\"\r\n"
        "\r\n"
        "--related-boundary\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "\r\n"
        "<html><body><img src=\"cid:hero-image\" alt=\"Hero\"></body></html>\r\n"
        "\r\n"
        "--related-boundary\r\n"
        "Content-Type: image/png\r\n"
        "Content-Disposition: inline\r\n"
        "Content-ID: <hero-image>\r\n"
        "\r\n"
        "inline image bytes\r\n"
        "--related-boundary--\r\n");

    test::check(parsed.attachments.size() == 1, "one inline attachment");
    test::check(parsed.attachments[0].is_inline, "inline attachment flag");
    test::check(parsed.attachments[0].content_id.value_or("") == "<hero-image>",
                "inline content id");
    test::check(parsed.attachments[0].content == "inline image bytes\n", "inline attachment body");
}

void test_mime_parser_decodes_quoted_printable_text() {
    const auto parsed = parse(
        "From: QA Sender <sender@example.com>\r\n"
        "To: foo@adb.com\r\n"
        "Subject: QP\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "Content-Transfer-Encoding: quoted-printable\r\n"
        "\r\n"
        "Hello=2C Rapid=20Inbox!=0AThis line is soft=\r\n"
        "continued with =5Funderscore=2E\r\n");

    test::check(parsed.text_body == "Hello, Rapid Inbox!\nThis line is softcontinued with _underscore.\n",
                "quoted printable decode");
}

void test_mime_parser_decodes_encoded_subject() {
    const auto parsed = parse(
        "From: QA Sender <sender@example.com>\r\n"
        "To: foo@adb.com\r\n"
        "Subject: =?UTF-8?B?SGVsbG8g?= =?UTF-8?Q?Rapid=5FInbox?=\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        "\r\n"
        "Body\r\n");

    test::check(parsed.subject.value_or("") == "Hello Rapid_Inbox", "encoded subject");
}

void test_mime_parser_reports_malformed_multipart() {
    bool threw = false;
    try {
        (void)parse(
            "Subject: Broken\r\n"
            "Content-Type: multipart/mixed; boundary=\"missing\"\r\n"
            "\r\n"
            "body without boundary\r\n");
    } catch (const ParseFailure&) {
        threw = true;
    }
    test::check(threw, "malformed multipart throws ParseFailure");
}
