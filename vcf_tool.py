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
    st.subheader("🔗 Merge and Clean Two VCF Files")
    st.markdown("_If you only want to clean one file, upload it twice._")
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

# def tool_clean_invalid():
#     st.subheader("🧹 Remove Invalid Contacts from a VCF File")
#     vcf_file = st.file_uploader("📤 Upload VCF File", type=["vcf"], key="cleanvcf")

#     if vcf_file and st.button("🧼 Clean Invalid Contacts"):
#         contacts = parse_vcf(vcf_file.read())
#         cleaned = []
#         discarded = []

#         for contact in contacts:
#             phones = extract_phones(contact)
#             if phones:
#                 cleaned.append(contact)
#             else:
#                 discarded.append((contact, 'invalid'))

#         st.success(f"✅ Cleaned. Valid contacts: {len(cleaned)}, Removed: {len(discarded)}")
#         st.download_button("📥 Download Cleaned VCF", create_vcf_file(cleaned), "cleaned_contacts.vcf", "text/vcard")
#         st.download_button("📄 Download PDF of Cleaned Contacts", generate_pdf_preview(cleaned), "cleaned_preview.pdf", "application/pdf")
#         st.download_button("🗂️ Download Removed Contacts PDF", generate_discarded_pdf(discarded), "removed.pdf", "application/pdf")

def tool_add_prefix():
    st.subheader("📝 Add Prefix to Contact Names")
    prefix = st.text_input("Enter Prefix (e.g., Kailash Yadav)", value="Kailash Yadav")
    vcf_file = st.file_uploader("📤 Upload VCF File", type=["vcf"], key="prefixvcf")

    if vcf_file and prefix and st.button("➕ Add Prefix"):
        lines = vcf_file.read().decode("utf-8").splitlines()
        prefix_qp = quopri.encodestring(prefix.encode("utf-8")).decode("utf-8")

        output = io.StringIO()
        contacts = []
        current_name = ""
        current_number = ""
        i = 0
        inside_vcard = False
        vcard_has_fn = False

        while i < len(lines):
            line = lines[i].rstrip('\n')

            if line == 'BEGIN:VCARD':
                inside_vcard = True
                vcard_has_fn = False
                current_name = ""
                current_number = ""
                output.write(line + '\n')

            elif line.startswith('FN;') and 'QUOTED-PRINTABLE' in line:
                full_line = line
                while full_line.endswith('=') and i + 1 < len(lines):
                    i += 1
                    full_line = full_line.rstrip('=') + lines[i].rstrip('\n')
                try:
                    header, qp_name = full_line.split(':', 1)
                    updated_qp_name = prefix_qp + '=20' + qp_name
                    output.write(f"{header}:{updated_qp_name}\n")
                    decoded_name = quopri.decodestring(qp_name).decode('utf-8', errors='ignore')
                    current_name = f"{prefix} {decoded_name}"
                    vcard_has_fn = True
                except:
                    output.write(full_line + '\n')

            elif line.startswith('FN:'):
                name = line[3:]
                updated_name = f"FN:{prefix} {name}\n"
                output.write(updated_name)
                current_name = f"{prefix} {name}"
                vcard_has_fn = True

            elif line.startswith('TEL'):
                output.write(line + '\n')
                try:
                    current_number = line.split(':')[1]
                except:
                    current_number = ""

            elif line == 'END:VCARD':
                if not vcard_has_fn:
                    output.write(f"FN:{prefix}\n")
                    current_name = prefix
                output.write(line + '\n')
                contacts.append((current_name.strip(), current_number.strip()))
                inside_vcard = False
            else:
                output.write(line + '\n')

            i += 1

        final_vcf = output.getvalue().encode("utf-8")
        st.success("✅ Prefix added successfully!")
        st.download_button("📥 Download Updated VCF", final_vcf, "updated_contacts.vcf", "text/vcard")
        st.download_button("📄 Download PDF Preview", generate_pdf_preview([f"FN:{name}\nTEL:{number}" for name, number in contacts]), "prefix_preview.pdf", "application/pdf")

# ----------------- Streamlit UI -----------------

st.set_page_config(page_title="VCF Toolbox", layout="centered")
st.title("🔧 VCF Toolbox")
# tool = st.sidebar.selectbox("Select Tool", ["Merge Contacts", "Add Prefix to Names","Remove Invalid Contacts"])
tool = st.sidebar.selectbox("Select Tool", ["Merge & Clean Contacts", "Add Prefix to Names"])

if tool == "Merge & Clean Contacts":
    tool_merge_contacts()
elif tool == "Add Prefix to Names":
    tool_add_prefix()
# elif tool == "Remove Invalid Contacts":
#     tool_clean_invalid()

