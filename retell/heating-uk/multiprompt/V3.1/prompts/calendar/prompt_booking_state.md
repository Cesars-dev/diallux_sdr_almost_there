# State: booking

Book the confirmed slot now via book_calendar.

The customer already confirmed {{selected_slot_label}}. Do NOT re-ask or change the slot.

Call `book_calendar` with:
- time: the slot's `time` field (bare Europe/London local, e.g. 2026-08-03T11:00:00) — copy from the check_availability result
- timezone: "Europe/London"
- name: {{customer_name}}
- email: "jaydiallux@gmail.com"
- attendeePhoneNumber: if known
- title: [Webhook Test]
- notes: [Webhook test booking]
- location: {{address_house_number}} {{address_street}}, {{address_city}}, {{address_postcode}}

After booking, confirm success or report failure naturally. Do not call book_calendar more than once.
