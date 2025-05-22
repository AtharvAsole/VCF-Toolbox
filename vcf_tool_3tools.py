import streamlit as st
import re
import io
import os
import quopri
from fpdf import FPDF

# ----------------- Helper Functions -----------------

# def normalize_phone(phone):
#     digits = re.sub(r'\D', '', phone)
#     if len(digits) == 10 and digits.startswith(('6', '7', '8', '9')):
#         return '91' + digits
#     if len(digits) == 11 and digits.startswith('0') and digits[1] in '6789':
#         return '91' + digits[1:]
#     if len(digits) == 12 and digits.startswith('91') and digits[2] in '6789':
#         return digits
#     return None

def normalize_phone(phone):
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10 and digits.startswith(('6', '7', '8', '9')):
        return '+91' + digits
    if len(digits) == 11 and digits.startswith('0') and digits[1] in '6789':
        return '+91' + digits[1:]
    if len(digits) == 12 and digits.startswith('91') and digits[2] in '6789':
        return '+91' + digits[2:]
    if len(digits) == 13 and digits.startswith('91') and digits[2] in '6789':  # for numbers already with +91
        return '+' + digits
    return None


def extract_phones(contact):
    phones = []
    for line in contact.splitlines():
        if line.strip().upper().startswith("TEL"):
            parts = line.split(':', 1)
            if len(parts) == 2:
                normalized = normalize_phone(parts[1])
                if normalized:
                    phones.append(normalized)
    return phones

def extract_contact_summary(contact):
    name = "Unknown"
    phones = []
    for line in contact.splitlines():
        if line.startswith("FN:") or line.startswith("N:"):
            name = line.split(':', 1)[1].strip()
        elif line.strip().upper().startswith("TEL"):
            parts = line.split(':', 1)
            if len(parts) == 2:
                raw = parts[1].strip()
                norm = normalize_phone(raw)
                if norm:
                    phones.append(norm)
    return name, phones

def parse_vcf(content):
    data = content.decode('utf-8', errors='ignore')
    contacts = data.strip().split('END:VCARD')
    clean_contacts = []
    for c in contacts:
        c = c.strip()
        if c:
            if not c.endswith('END:VCARD'):
                c += '\nEND:VCARD'
            clean_contacts.append(c)
    return clean_contacts

def create_vcf_file(contacts):
    output = io.StringIO()
    for contact in contacts:
        output.write(contact.strip() + '\n')
    return output.getvalue().encode('utf-8')

def register_unicode_font(pdf):
    font_path = "arial-unicode-ms.ttf"
    if os.path.exists(font_path):
        pdf.add_font("ArialUnicode", "", font_path, uni=True)
        pdf.set_font("ArialUnicode", size=12)
    else:
        pdf.set_font("Helvetica", size=12)

def generate_pdf_preview(contacts, title="Contacts Preview"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    register_unicode_font(pdf)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    pdf.ln(5)

    for idx, contact in enumerate(contacts, 1):
        name, phones = extract_contact_summary(contact)
        pdf.cell(200, 10, txt=f"{idx}. {name} - {', '.join(phones)}", ln=True)

    pdf_string = pdf.output(dest='S').encode('latin-1')
    return io.BytesIO(pdf_string)

def generate_discarded_pdf(discarded_contacts):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    register_unicode_font(pdf)
    pdf.cell(200, 10, txt="Discarded Contacts Report", ln=True, align='C')
    pdf.ln(5)

    for idx, (contact, reason) in enumerate(discarded_contacts, 1):
        name, phones = extract_contact_summary(contact)
        reason_label = "❌ Duplicate" if reason == 'duplicate' else "⚠️ Invalid Number"
        phones_display = ', '.join(phones) if phones else "No valid number"
        pdf.cell(200, 10, txt=f"{idx}. {name} - {phones_display}  ({reason_label})", ln=True)

    pdf_string = pdf.output(dest='S').encode('latin-1')
    return io.BytesIO(pdf_string)

# ----------------- Tools -----------------

def tool_merge_contacts():
    st.subheader("🔗 Merge Two VCF Files")
    vcf1 = st.file_uploader("📤 Upload First VCF File", type=["vcf"], key="vcf1")
    vcf2 = st.file_uploader("📤 Upload Second VCF File", type=["vcf"], key="vcf2")

    if vcf1 and vcf2:
        if st.button("🔄 Merge Contacts"):
            contacts1 = parse_vcf(vcf1.read())
            contacts2 = parse_vcf(vcf2.read())
            all_contacts = contacts1 + contacts2

            seen_numbers = set()
            merged = []
            discarded = []

            for contact in all_contacts:
                phones = extract_phones(contact)
                if not phones:
                    discarded.append((contact, 'invalid'))
                    continue
                if any(phone in seen_numbers for phone in phones):
                    discarded.append((contact, 'duplicate'))
                    continue
                merged.append(contact)
                seen_numbers.update(phones)

            if merged:
                st.success(f"✅ Merged {len(merged)} contacts successfully!")
                st.info(f"🗑️ Discarded {len(discarded)} contacts")

                st.download_button("📥 Download Merged VCF", create_vcf_file(merged), "merged.vcf", "text/vcard")
                st.download_button("📄 Download Merged Contacts PDF", generate_pdf_preview(merged), "merged_preview.pdf", "application/pdf")
                st.download_button("🗂️ Download Discarded Contacts PDF", generate_discarded_pdf(discarded), "discarded.pdf", "application/pdf")
            else:
                st.warning("⚠️ No valid or unique contacts found.")

def tool_clean_invalid():
    st.subheader("🧹 Remove Invalid Contacts from a VCF File")
    vcf_file = st.file_uploader("📤 Upload VCF File", type=["vcf"], key="cleanvcf")

    if vcf_file and st.button("🧼 Clean Invalid Contacts"):
        contacts = parse_vcf(vcf_file.read())
        cleaned = []
        discarded = []

        for contact in contacts:
            phones = extract_phones(contact)
            if phones:
                cleaned.append(contact)
            else:
                discarded.append((contact, 'invalid'))

        st.success(f"✅ Cleaned. Valid contacts: {len(cleaned)}, Removed: {len(discarded)}")
        st.download_button("📥 Download Cleaned VCF", create_vcf_file(cleaned), "cleaned_contacts.vcf", "text/vcard")
        st.download_button("📄 Download PDF of Cleaned Contacts", generate_pdf_preview(cleaned), "cleaned_preview.pdf", "application/pdf")
        st.download_button("🗂️ Download Removed Contacts PDF", generate_discarded_pdf(discarded), "removed.pdf", "application/pdf")

def tool_add_prefix():
    st.subheader("📝 Add Prefix to Contact Names")
    prefix = st.text_input("Enter Prefix (e.g., Kailash Yadav)", value="Kailash Yadav")
    vcf_file = st.file_uploader("📤 Upload VCF File", type=["vcf"], key="prefixvcf")

    if vcf_file and prefix and st.button("➕ Add Prefix"):
        lines = vcf_file.read().decode("utf-8").splitlines()
        prefix_qp = quopri.encodestring(prefix.encode("utf-8")).decode("utf-8")

        output = io.StringIO()
        updated_contacts = []
        contact_lines = []
        current_name = ""
        current_number = ""
        inside_vcard = False
        vcard_has_fn = False

        for i, line in enumerate(lines):
            line = line.rstrip('\n')

            if line == 'BEGIN:VCARD':
                inside_vcard = True
                vcard_has_fn = False
                contact_lines = [line]
                current_name = ""
                current_number = ""

            elif line == 'END:VCARD':
                if not vcard_has_fn:
                    contact_lines.append(f"FN:{prefix}")
                    current_name = prefix
                contact_lines.append(line)
                updated_contacts.append('\n'.join(contact_lines))
                inside_vcard = False

            elif inside_vcard:
                if line.startswith('FN;') and 'QUOTED-PRINTABLE' in line:
                    full_line = line
                    while full_line.endswith('=') and i + 1 < len(lines):
                        i += 1
                        full_line = full_line.rstrip('=') + lines[i].rstrip('\n')
                    try:
                        header, qp_name = full_line.split(':', 1)
                        updated_qp_name = prefix_qp + '=20' + qp_name
                        contact_lines.append(f"{header}:{updated_qp_name}")
                        decoded_name = quopri.decodestring(qp_name).decode('utf-8', errors='ignore')
                        current_name = f"{prefix} {decoded_name}"
                        vcard_has_fn = True
                    except:
                        contact_lines.append(full_line)

                elif line.startswith('FN:'):
                    name = line[3:]
                    updated_name = f"{prefix} {name}"
                    contact_lines.append(f"FN:{updated_name}")
                    current_name = updated_name
                    vcard_has_fn = True

                elif line.startswith('TEL'):
                    contact_lines.append(line)
                    try:
                        current_number = line.split(':')[1]
                    except:
                        current_number = ""

                else:
                    contact_lines.append(line)

        final_vcf = '\n'.join(updated_contacts).encode("utf-8")
        st.success("✅ Prefix added successfully!")
        st.download_button("📥 Download Updated VCF", final_vcf, "updated_contacts.vcf", "text/vcard")

        # Generate PDF preview
        st.download_button(
            "📄 Download PDF Preview",
            generate_pdf_preview(updated_contacts, "Prefix Contacts Preview"),
            "prefix_preview.pdf",
            "application/pdf"
        )



# Tool to remove contact from keyword
def tool_remove_by_keyword():
    st.subheader("🗂️ Remove Contacts by Keyword")
    vcf_file = st.file_uploader("📤 Upload VCF File", type=["vcf"], key="keywordvcf")
    keyword_input = st.text_input("🔍 Enter keywords to filter out (comma-separated)", placeholder="e.g. TCS, Friend, xyz")

    if vcf_file and keyword_input and st.button("🚫 Remove Matching Contacts"):
        keywords = [k.strip().lower() for k in keyword_input.split(',') if k.strip()]
        contacts = parse_vcf(vcf_file.read())
        retained = []
        removed = []

        for contact in contacts:
            name, _ = extract_contact_summary(contact)
            if any(keyword in name.lower() for keyword in keywords):
                removed.append((contact, 'keyword'))
            else:
                retained.append(contact)

        st.success(f"✅ Contacts retained: {len(retained)}, Removed due to keywords: {len(removed)}")

        st.download_button("📥 Download Cleaned VCF", create_vcf_file(retained), "keyword_cleaned.vcf", "text/vcard")
        st.download_button("📄 Download PDF of Retained Contacts", generate_pdf_preview(retained), "retained_preview.pdf", "application/pdf")
        st.download_button("📄 Download Removed Contacts PDF", generate_discarded_pdf(removed), "keyword_removed.pdf", "application/pdf")



# def tool_remove_existing_contacts_by_number():
#     st.subheader("🧹 Remove Contacts from File 2 if Number Exists in File 1")

#     file1 = st.file_uploader("📁 Upload VCF File 1 (Reference - contains numbers to remove)", type=["vcf"], key="refvcf")
#     file2 = st.file_uploader("📁 Upload VCF File 2 (Target - from which contacts will be removed)", type=["vcf"], key="targetvcf")

#     if file1 and file2 and st.button("🚫 Remove Matching Contacts by Number"):
#         def extract_contacts(file):
#             raw_lines = file.read().decode("utf-8").splitlines()
#             contacts = []
#             current_contact = []
#             inside_vcard = False
#             for line in raw_lines:
#                 if line == "BEGIN:VCARD":
#                     inside_vcard = True
#                     current_contact = [line]
#                 elif line == "END:VCARD":
#                     current_contact.append(line)
#                     contacts.append("\n".join(current_contact))
#                     inside_vcard = False
#                 elif inside_vcard:
#                     current_contact.append(line)
#             return contacts

#         def extract_number(contact):
#             lines = contact.splitlines()
#             for line in lines:
#                 if line.startswith("TEL"):
#                     try:
#                         return line.split(":")[1].strip()
#                     except:
#                         return ""
#             return ""

#         # Extract numbers from File 1
#         reference_contacts = extract_contacts(file1)
#         reference_numbers = set()
#         for contact in reference_contacts:
#             number = extract_number(contact)
#             if number:
#                 reference_numbers.add(number)

#         # Filter File 2 contacts
#         target_contacts = extract_contacts(file2)
#         filtered_contacts = []
#         removed_count = 0
#         for contact in target_contacts:
#             number = extract_number(contact)
#             if number not in reference_numbers:
#                 filtered_contacts.append(contact)
#             else:
#                 removed_count += 1

#         # Create cleaned VCF
#         cleaned_vcf = '\n'.join(filtered_contacts).encode("utf-8")
#         st.success(f"✅ Removed {removed_count} contact(s) from File 2 based on matching phone number.")

#         st.download_button("📥 Download Cleaned VCF", cleaned_vcf, "cleaned_contacts.vcf", "text/vcard")


def tool_remove_existing_contacts_by_number():
    st.subheader("🧹 Remove Contacts from File 2 if Number Exists in File 1")

    file1 = st.file_uploader("📁 Upload VCF File 1 (Reference - numbers to remove)", type=["vcf"], key="refvcf")
    file2 = st.file_uploader("📁 Upload VCF File 2 (Target - from which contacts will be removed)", type=["vcf"], key="targetvcf")

    if file1 and file2 and st.button("🚫 Remove Matching Contacts by Number"):
        def extract_contacts(file):
            raw_lines = file.read().decode("utf-8").splitlines()
            contacts = []
            current_contact = []
            inside_vcard = False
            for line in raw_lines:
                if line == "BEGIN:VCARD":
                    inside_vcard = True
                    current_contact = [line]
                elif line == "END:VCARD":
                    current_contact.append(line)
                    contacts.append("\n".join(current_contact))
                    inside_vcard = False
                elif inside_vcard:
                    current_contact.append(line)
            return contacts

        def extract_number(contact):
            lines = contact.splitlines()
            for line in lines:
                if line.startswith("TEL"):
                    try:
                        return line.split(":")[1].strip()
                    except:
                        return ""
            return ""

        # Extract contacts and numbers from File 1
        reference_contacts = extract_contacts(file1)
        reference_numbers = set()
        for contact in reference_contacts:
            number = extract_number(contact)
            if number:
                reference_numbers.add(number)

        # Extract contacts from File 2 and split by removal condition
        target_contacts = extract_contacts(file2)
        retained_contacts = []
        removed_contacts = []

        for contact in target_contacts:
            number = extract_number(contact)
            if number and number in reference_numbers:
                removed_contacts.append(contact)
            else:
                retained_contacts.append(contact)

        # Prepare cleaned VCF for download
        cleaned_vcf = '\n'.join(retained_contacts).encode("utf-8")

        st.success(f"✅ Removed {len(removed_contacts)} contact(s) from File 2 based on matching phone number.")
        st.info(f"Remaining contacts: {len(retained_contacts)}")

        st.download_button("📥 Download Cleaned VCF (File 2 after removal)", cleaned_vcf, "cleaned_contacts.vcf", "text/vcard")

        if removed_contacts:
            st.download_button(
                "📄 Download PDF of Removed Contacts",
                generate_pdf_preview(removed_contacts, title="Removed Contacts"),
                "removed_contacts.pdf",
                "application/pdf",
            )

        if retained_contacts:
            st.download_button(
                "📄 Download PDF of Remaining Contacts",
                generate_pdf_preview(retained_contacts, title="Remaining Contacts"),
                "remaining_contacts.pdf",
                "application/pdf",
            )

# ----------------- Streamlit UI -----------------

st.set_page_config(page_title="VCF Toolbox", layout="centered")
st.title("🔧 VCF Toolbox")
tool = st.sidebar.selectbox("Select Tool", [
    "Merge Contacts", 
    "Add Prefix to Names", 
    "Remove Invalid Contacts", 
    "Remove Contacts by Keyword",
    "Remove Duplicate Contacts (by number from another VCF)"
])


if tool == "Merge Contacts":
    tool_merge_contacts()
elif tool == "Add Prefix to Names":
    tool_add_prefix()
elif tool == "Remove Invalid Contacts":
    tool_clean_invalid()
elif tool == "Remove Contacts by Keyword":
    tool_remove_by_keyword()
elif tool == "Remove Duplicate Contacts (by number from another VCF)":
    tool_remove_existing_contacts_by_number()


