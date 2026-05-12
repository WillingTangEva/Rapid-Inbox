#include "../src/domain_matcher.h"
#include "../src/mail_queue.h"
#include "../src/smtp_session.h"

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
