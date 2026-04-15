// --- PREMIUM BOOKING STATE ---
let currentStep = 1;
let selectedPrice = 100;
let selectedTier = "Adult";
let qty = 2;
let selectedPaymentMethod = 'upi';

function openBooking() {
    document.getElementById('bookingModal').style.display = 'flex';
    goStep(1);
    updateSummary();
}

function closeBooking() {
    document.getElementById('bookingModal').style.display = 'none';
}

function handleOverlayClick(e) {
    if (e.target.id === 'bookingModal') closeBooking();
}

function goStep(step) {
    // Hide all panels
    document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
    // Show target
    document.getElementById(`step${step}`).classList.add('active');
    currentStep = step;

    // Update Dots
    for (let i = 1; i <= 4; i++) {
        const dot = document.getElementById(`pd${i}`);
        if (dot) {
            if (i <= step) dot.classList.add('active');
            else dot.classList.remove('active');
        }
    }

    if (step === 3) updateSummary();
}

function selectTicket(el, price, tier) {
    document.querySelectorAll('.ticket-card-mini').forEach(t => t.classList.remove('selected'));
    el.classList.add('selected');
    selectedPrice = price;
    selectedTier = tier;
    updateSummary();
}

function changeQty(delta) {
    qty = Math.max(1, qty + delta);
    document.getElementById('qtyVal').textContent = qty.toString().padStart(2, '0');
    updateSummary();
}

function updateSummary() {
    const museum = document.getElementById('museumSelect').value || "Not Selected";
    const date = document.getElementById('visitDate').value || "Not Selected";
    const visitor = document.getElementById('visitorName').value || "Guest";
    const total = selectedPrice * qty;

    // Update Sidebar
    const sumMuseum = document.getElementById('sumMuseum');
    const sumDate = document.getElementById('sumDate');
    const sumQty = document.getElementById('sumQty');
    const sumTotal = document.getElementById('sumTotal');

    if(sumMuseum) sumMuseum.textContent = museum.split(',')[0];
    if(sumDate) sumDate.textContent = date;
    if(sumQty) sumQty.textContent = `${qty} Ã— ${selectedTier}`;
    if(sumTotal) sumTotal.textContent = `â‚¹${total}`;

    // Update QR scan amount if visible
    const scanAmt = document.getElementById('scanAmount');
    if (scanAmt) scanAmt.textContent = total;
}

function selectPayment(method, el) {
    document.querySelectorAll('.pay-option').forEach(m => m.classList.remove('selected'));
    el.classList.add('selected');
    selectedPaymentMethod = method;
    
    // Toggle UI
    if(method === 'upi') {
        document.getElementById('payUPI').style.display = 'block';
        document.getElementById('payCard').style.display = 'none';
    } else if(method === 'card') {
        document.getElementById('payUPI').style.display = 'none';
        document.getElementById('payCard').style.display = 'block';
    }
}

async function processManualPayment() {
    const museum = document.getElementById('museumSelect').value;
    const visitor = document.getElementById('visitorName').value;
    const total = selectedPrice * qty;

    if (!museum || museum === "") {
        alert("Please select a destination museum.");
        goStep(1);
        return;
    }
    
    // STRICT PAYMENT VALIDATION
    if (selectedPaymentMethod === 'upi') {
        const utr = document.getElementById('utrInput').value.trim();
        if (utr.length < 12) {
            alert("Payment Verification Failed: Please complete the UPI payment using the QR code and enter the valid 12-digit UTR/Reference number.");
            return;
        }
    } else if (selectedPaymentMethod === 'card') {
        const cardNo = document.getElementById('cardNumberInput').value.trim();
        const cvv = document.getElementById('cardCvvInput').value.trim();
        if (cardNo.length < 16 || cvv.length < 3) {
            alert("Payment Failed: Please enter valid 16-digit credit/debit card details.");
            return;
        }
    }

    const btn = document.getElementById('payBtn');
    const originalContent = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    btn.disabled = true;

    // Simulate Payment Gateway Network Delay
    await new Promise(r => setTimeout(r, 1800));

    // For Demo: Randomly simulate a payment failure (10% chance)
    if (Math.random() < 0.10) {
        alert("Payment Gateway Error: Bank server did not respond. Your account has not been charged.");
        btn.innerHTML = originalContent;
        btn.disabled = false;
        return;
    }

    try {
        const response = await fetch('/api/manual_book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                museum: museum,
                visitor_name: visitor,
                count: qty,
                total: total
            })
        });
        const data = await response.json();

        if (data.success) {
            document.getElementById('ticketNum').textContent = data.ticket_no;
            document.getElementById('ticketMuseumText').textContent = museum;
            document.getElementById('ticketVisitorText').textContent = visitor;
            goStep(4);
        } else {
            alert(data.message || "Booking encountered a problem.");
        }
    } catch (err) {
        alert("Connectivity issue. Please try again.");
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

async function downloadTicket() {
    const ticketDiv = document.querySelector('.e-ticket-modern');
    if (!ticketDiv) return;
    
    try {
        // Use html2canvas to convert the ticket component to an image
        const canvas = await html2canvas(ticketDiv, {
            scale: 2, // Enhances quality
            backgroundColor: '#11111d' 
        });
        
        // Trigger download
        const link = document.createElement('a');
        link.download = `Museum_E_Ticket_${document.getElementById('ticketNum').textContent}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    } catch (err) {
        console.error("Download Error:", err);
        alert("Failed to download the ticket. Please try again or take a screenshot.");
    }
}

// --- AI CHATBOT POLYGLOT LOGIC ---
function toggleChat() {
    const chatWidget = document.getElementById('chatWidget');
    const chatHint = document.querySelector('.chat-hint');
    
    if (chatWidget.style.display === 'none') {
        chatWidget.style.display = 'flex';
        if (chatHint) chatHint.style.display = 'none';
    } else {
        chatWidget.style.display = 'none';
        if (chatHint) chatHint.style.display = 'block';
    }
}

async function sendMessage(text) {
    const input = document.getElementById('chatInput');
    const chatBody = document.getElementById('chatBody');
    const typing = document.getElementById('chatTyping');
    const message = text || input.value.trim();

    if (!message) return;

    // Append User Message
    const userDiv = document.createElement('div');
    userDiv.className = 'message user-message';
    userDiv.textContent = message;
    chatBody.appendChild(userDiv);
    if (!text) input.value = '';
    chatBody.scrollTop = chatBody.scrollHeight;

    // Show Typing
    typing.style.display = 'block';
    chatBody.scrollTop = chatBody.scrollHeight;

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message })
        });

        const data = await response.json();
        
        // Hide Typing
        typing.style.display = 'none';

        if (response.status === 401) {
            appendBotMessage("I am sorry, but you must <a href='/login' style='color:var(--primary-gold)'>log in</a> before I can process your reservation.");
            return;
        }

        appendBotMessage(data.response);
    } catch (err) {
        typing.style.display = 'none';
        appendBotMessage("I apologize, but my connection seems to have faltered. Please try again.");
    }
}

function quickAction(text) {
    sendMessage(text);
}


function appendBotMessage(html) {
    const chatBody = document.getElementById('chatBody');
    const botMsgContainer = document.createElement('div');
    botMsgContainer.style.display = 'flex';
    botMsgContainer.style.gap = '10px';
    botMsgContainer.style.marginBottom = '15px';
    botMsgContainer.style.alignItems = 'flex-start';

    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'virtual-curator-avatar';
    avatarDiv.innerHTML = `
        <svg width="35" height="35" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="20" cy="20" r="18" stroke="rgba(197, 160, 89, 0.3)" stroke-width="0.5" />
            <g fill="#c5a059">
                <path d="M6 15 L20 4 L34 15 H6Z" />
                <rect x="9" y="17" width="2" height="14" rx="0.5" />
                <rect x="16" y="17" width="2" height="14" rx="0.5" />
                <rect x="22" y="17" width="2" height="14" rx="0.5" />
                <rect x="29" y="17" width="2" height="14" rx="0.5" />
                <rect x="6" y="31" width="28" height="3" rx="1" />
            </g>
        </svg>
    `;

    const botDiv = document.createElement('div');
    botDiv.className = 'message bot-message';
    botDiv.style.margin = '0';
    botDiv.innerHTML = html;

    botMsgContainer.appendChild(avatarDiv);
    botMsgContainer.appendChild(botDiv);
    chatBody.appendChild(botMsgContainer);
    chatBody.scrollTop = chatBody.scrollHeight;
}

function handleKeyPress(e) {
    if (e.key === 'Enter') sendMessage();
}

function openPaymentModal(amount) {
    document.getElementById('bookingModal').style.display = 'flex';
    selectedPrice = amount;
    qty = 1;
    selectedTier = "Direct Booking";
    goStep(3);
}

// --- GLOBAL UI EFFECTS ---
const revealObs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible'); });
}, { threshold: 0.1 });

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));
});

let lastScrollTop = 0;
window.addEventListener('scroll', () => {
    const nav = document.getElementById('navbar');
    let scrollTop = window.pageYOffset || document.documentElement.scrollTop;

    // Smart Sticky Header: Hide on scroll down, show on scroll up
    if (scrollTop > lastScrollTop && scrollTop > 150) {
        nav.classList.add('nav-hidden');
    } else {
        nav.classList.remove('nav-hidden');
    }
    lastScrollTop = scrollTop <= 0 ? 0 : scrollTop;

    // Visual State: Transparent at top, solid while scrolling
    if (scrollTop > 50) {
        nav.style.padding = '12px 8%';
        nav.style.background = 'rgba(10, 10, 9, 0.85)';
        nav.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
    } else {
        nav.style.padding = '20px 8%';
        nav.style.background = 'transparent';
        nav.style.boxShadow = 'none';
    }
});

