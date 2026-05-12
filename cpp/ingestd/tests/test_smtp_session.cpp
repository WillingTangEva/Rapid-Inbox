#include "../src/domain_matcher.h"
#include "../src/mail_queue.h"
#include "../src/smtp_session.h"

#include <chrono>
#include <string>

namespace test {
void check(bool condition, const std::string& message);
}

void test_smtp_session_accepts_valid_message() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("EHLO client") == "250 rapid-inbox-ingestd", "ehlo");
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "250 OK", "rcpt");
    test::check(session.handle_line("DATA") == "354 End data with <CR><LF>.<CR><LF>", "data");
    test::check(session.handle_line("Subject: Hi") == "", "data line no response");
    test::check(session.handle_line("") == "", "blank data line");
    const std::string queued = session.handle_line(".");
    test::check(queued.rfind("250 queued as msg_", 0) == 0, "queued response");
    auto batch = queue.pop_batch(10, std::chrono::milliseconds(1));
    test::check(batch.size() == 1, "queued one job");
    test::check(batch[0].recipients[0].match.address_canonical == "code@adb.com", "canonical recipient");
}

void test_smtp_session_rejects_unknown_domain() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@unknown.com>") == "550 domain not allowed", "unknown rejected");
}

void test_smtp_session_rejects_prefix_collision_commands() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("EHLOX client") == "502 command not implemented", "ehlox rejected");
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "250 OK", "rcpt");
    test::check(session.handle_line("DATAX") == "502 command not implemented", "datax rejected");
    test::check(session.handle_line("DATA") == "354 End data with <CR><LF>.<CR><LF>", "data still accepted");
}

void test_smtp_session_clears_transaction_after_queueing() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "250 OK", "rcpt");
    test::check(session.handle_line("DATA") == "354 End data with <CR><LF>.<CR><LF>", "data");
    test::check(session.handle_line("Subject: First") == "", "body");
    test::check(session.handle_line(".").rfind("250 queued as msg_", 0) == 0, "queued");
    test::check(session.handle_line("DATA") == "554 no valid recipients", "second data rejects stale recipients");
    auto batch = queue.pop_batch(10, std::chrono::milliseconds(1));
    test::check(batch.size() == 1, "only first message queued");
}

void test_smtp_session_rejects_rcpt_before_mail_from() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "503 need MAIL FROM first", "rcpt before mail");
    test::check(session.handle_line("DATA") == "554 no valid recipients", "no recipient after rejected rcpt");
}

void test_smtp_session_rejects_empty_mail_from_without_changing_state() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("MAIL FROM:<>") == "501 invalid sender", "empty sender rejected");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "503 need MAIL FROM first", "empty sender not set");
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "valid sender");
    test::check(session.handle_line("MAIL FROM:   ") == "501 invalid sender", "blank sender rejected");
    test::check(session.handle_line("MAIL FROM:<broken@example.com") == "501 invalid sender", "malformed sender rejected");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "250 OK", "valid sender retained");
    test::check(session.handle_line("DATA") == "354 End data with <CR><LF>.<CR><LF>", "data");
    test::check(session.handle_line(".").rfind("250 queued as msg_", 0) == 0, "queued");
    auto batch = queue.pop_batch(10, std::chrono::milliseconds(1));
    test::check(batch.size() == 1, "queued one message");
    test::check(batch[0].envelope_from == "sender@example.com", "invalid sender did not replace valid sender");
}

void test_smtp_session_rejects_data_arguments() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "250 OK", "rcpt");
    test::check(session.handle_line("DATA anything") == "502 command not implemented", "data arguments rejected");
    test::check(session.handle_line("DATA") == "354 End data with <CR><LF>.<CR><LF>", "bare data accepted");
}

void test_smtp_session_discards_oversized_data_until_terminator() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(10);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 5);
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "250 OK", "rcpt");
    test::check(session.handle_line("DATA") == "354 End data with <CR><LF>.<CR><LF>", "data");
    test::check(session.handle_line("123456") == "552 message too large", "oversize response");
    test::check(session.handle_line("EHLO body") == "", "oversize body discarded");
    test::check(session.handle_line(".") == "", "oversize terminator discarded");
    test::check(session.handle_line("DATA") == "554 no valid recipients", "oversize transaction cleared");
    auto batch = queue.pop_batch(10, std::chrono::milliseconds(1));
    test::check(batch.empty(), "oversize message not queued");
}

void test_smtp_session_reports_queue_full() {
    rapid_inbox::ingestd::DomainMatcher matcher({{1, "adb.com", true, true, "keep", false}});
    rapid_inbox::ingestd::MailQueue queue(0);
    rapid_inbox::ingestd::SmtpSession session(matcher, queue, 20, 1024 * 1024);
    test::check(session.handle_line("MAIL FROM:<sender@example.com>") == "250 OK", "mail from");
    test::check(session.handle_line("RCPT TO:<Code@adb.com>") == "250 OK", "rcpt");
    test::check(session.handle_line("DATA") == "354 End data with <CR><LF>.<CR><LF>", "data");
    test::check(session.handle_line("Subject: Full") == "", "body");
    test::check(session.handle_line(".") == "451 temporary queue full", "queue full response");
    test::check(queue.size() == 0, "queue remains empty");
}
