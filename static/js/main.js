$(document).ready(function () {
    const admissionEnquiryPurpose = "Admission Enquiry";
    const rollNoPattern = /^(AIE|CSE|CCE|AID)(23|24|25)(\d{3})$/;
    const $purpose = $("#purpose");
    const $studentFields = $(".student-field");
    const $studentRequiredFields = $("[data-student-required='true']");

    function isValidRollNo(value) {
        const normalizedValue = value.trim().toUpperCase();
        const match = normalizedValue.match(rollNoPattern);
        if (!match) {
            return false;
        }

        const sectionDigits = match[3];
        return ["0", "1", "2"].includes(sectionDigits[0]) && sectionDigits !== "000";
    }

    function toggleStudentFields() {
        const isAdmissionEnquiry = $purpose.val() === admissionEnquiryPurpose;

        $studentFields.toggleClass("d-none", isAdmissionEnquiry);
        $studentRequiredFields.each(function () {
            $(this).prop("required", !isAdmissionEnquiry);
            $(this).prop("disabled", isAdmissionEnquiry);
            $(this).removeClass("is-invalid");
        });
    }

    if ($purpose.length) {
        toggleStudentFields();
        $purpose.on("change", function () {
            toggleStudentFields();
            $("#formError").addClass("d-none");
        });
    }

    $("#visitorForm").on("submit", function (e) {
        let valid = true;

        $(this).find("[required]").each(function () {
            if ($(this).val().trim() === "") {
                $(this).addClass("is-invalid");
                valid = false;
            } else {
                $(this).removeClass("is-invalid");
            }
        });

        // Phone: must be 10 digits
        let phone = $("#phone").val().trim();
        if (!/^\d{10}$/.test(phone)) {
            $("#phone").addClass("is-invalid");
            valid = false;
        }

        if (!$("#rollNo").prop("disabled")) {
            let rollNo = $("#rollNo").val().trim().toUpperCase();
            $("#rollNo").val(rollNo);
            if (!isValidRollNo(rollNo)) {
                $("#rollNo").addClass("is-invalid");
                valid = false;
            }
        }

        if (!valid) {
            e.preventDefault();
            $("#formError").removeClass("d-none");
        }
    });

    $("input, select").on("input change", function () {
        $(this).removeClass("is-invalid");
        $("#formError").addClass("d-none");
    });

});
