// --- PREMIUM BOOKING STATE ---
let currentStep = 1;
let selectedPrice = 100;
let selectedTier = "Adult";
let qty = 2;
let selectedPaymentMethod = 'upi';
let payPollInterval = null;

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
    if(sumQty) sumQty.textContent = `${qty} × ${selectedTier}`;
    if(sumTotal) sumTotal.textContent = `₹${total}`;

    // Update QR scan amount if visible
    const scanAmt = document.getElementById('qrAmount');
    if (scanAmt) scanAmt.textContent = total.toFixed(2);
}

function selectPayment(method, el) {
    document.querySelectorAll('.pay-option').forEach(m => m.classList.remove('selected'));
    el.classList.add('selected');
    selectedPaymentMethod = method;
    
    // Toggle UI
    if(method === 'upi') {
        document.getElementById('payUPI').style.display = 'block';
        document.getElementById('payCard').style.display = 'none';
        // Auto-initialize QR display if not yet shown
        document.getElementById('qrAmount').textContent = (selectedPrice * qty).toFixed(2);
    } else if(method === 'card') {
        document.getElementById('payUPI').style.display = 'none';
        document.getElementById('payCard').style.display = 'block';
    }
}

function openPaymentModal(total, museumTitle, count, visitDate, visitorName) {
    // 1. Open Modal
    document.getElementById('bookingModal').style.display = 'flex';
    
    // 2. Pre-fill data
    const museumSelect = document.getElementById('museumSelect');
    // Try to find matching option by text
    for (let i = 0; i < museumSelect.options.length; i++) {
        if (museumSelect.options[i].text.toLowerCase().includes(museumTitle.toLowerCase())) {
            museumSelect.selectedIndex = i;
            break;
        }
    }
    
    if(visitorName) document.getElementById('visitorName').value = visitorName;
    if(visitDate) document.getElementById('visitDate').value = visitDate;
    
    qty = count;
    document.getElementById('qtyVal').textContent = qty.toString().padStart(2, '0');
    
    // 3. Set Price/Tier logic (Student = ₹1, else Adult/Standard)
    if (total / count === 1) {
        selectedPrice = 1;
        selectedTier = "Student";
    } else {
        selectedPrice = total / count;
        selectedTier = "Adult";
    }
    
    // 4. Update UI and jump to Payment
    updateSummary();
    goStep(3);
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

    const btn = document.getElementById('payBtn');
    const originalContent = btn.innerHTML;
    
    try {
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Initializing...';
        btn.disabled = true;

        // 1. Create Order on Backend
        const orderResp = await fetch('/api/create_razorpay_order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: total })
        });
        const orderData = await orderResp.json();

        if (!orderData.success) {
            if (orderData.message.includes('placeholder') || orderData.message.includes('Authentication failed')) {
                console.log("Using Mock Verification (Razorpay Credentials Missing/Invalid)");
                return demoPaymentFlow(museum, visitor, total, btn, originalContent);
            }
            throw new Error(orderData.message);
        }

        const orderId = orderData.order_id;
        console.log("Order Created:", orderId);

        if (selectedPaymentMethod === 'upi') {
            console.log("UPI Payment Selected, Generating QR...");
            // --- NEW DYNAMIC SCANNER FLOW ---
            document.getElementById('qrPlaceholder').style.display = 'flex';
            document.getElementById('dynamicQR').style.display = 'none';
            document.getElementById('payStatusLabel').textContent = "Generating Scanner...";
            document.getElementById('qrAmount').textContent = total.toFixed(2);

            const qrResp = await fetch('/api/generate_upi_qr', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ order_id: orderId, amount: total })
            });

            console.log("QR Response Received Status:", qrResp.status);
            if (!qrResp.ok) throw new Error(`Server returned ${qrResp.status}`);
            
            const qrData = await qrResp.json();
            console.log("QR Data:", qrData);

            if (qrData.success) {
                document.getElementById('qrPlaceholder').style.display = 'none';
                document.getElementById('dynamicQR').src = qrData.qr_code;
                document.getElementById('dynamicQR').style.display = 'block';
                document.getElementById('payStatusLabel').textContent = "Scan & Pay Now";
                document.getElementById('payStatusSub').style.display = 'block';
                
                // Start Polling
                startPaymentPolling(orderId, museum, visitor, total, qrData.payment_link_id);
            } else {
                throw new Error("Failed to generate QR");
            }
        } else {
            // --- STANDARD RAZORPAY MODAL FOR CARD ---
            const options = {
                "key": window.RZP_KEY_ID || "rzp_test_placeholder", 
                "amount": total * 100,
                "currency": "INR",
                "name": "MuseumBot Ticketing",
                "description": `Booking for ${museum}`,
                "order_id": orderId,
                "handler": async function (response) {
                    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying...';
                    const verifyResp = await fetch('/api/verify_razorpay_payment', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_signature: response.razorpay_signature,
                            museum: museum,
                            visitor_name: visitor,
                            visit_date: document.getElementById('visitDate').value || "Not Selected",
                            count: qty,
                            total: total
                        })
                    });
                    const verifyData = await verifyResp.json();
                    if (verifyData.success) {
                        document.getElementById('ticketNum').textContent = verifyData.ticket_no;
                        document.getElementById('ticketVisitorText').textContent = visitor || "Valued Guest";
                        document.getElementById('ticketMuseumText').textContent = museum;
                        goStep(4);
                    } else {
                        alert("Payment Verification Failed: " + verifyData.message);
                    }
                },
                "prefill": { "name": visitor, "email": "visitor@example.com" },
                "theme": { "color": "#c5a059" }
            };
            const rzp1 = new Razorpay(options);
            rzp1.open();
        }

        btn.innerHTML = originalContent;
        btn.disabled = false;

    } catch (err) {
        console.error(err);
        // Hide loading states on error
        const qrPl = document.getElementById('qrPlaceholder');
        if (qrPl) qrPl.style.display = 'none';
        const stLbl = document.getElementById('payStatusLabel');
        if (stLbl) stLbl.textContent = "Error Generating QR";
        
        alert("Payment Error: " + err.message);
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

function startPaymentPolling(orderId, museum, visitor, total, linkId = null) {
    if (payPollInterval) clearInterval(payPollInterval);
    
    payPollInterval = setInterval(async () => {
        try {
            const resp = await fetch('/api/check_payment_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    order_id: orderId,
                    payment_link_id: linkId,
                    museum: museum,
                    visitor_name: visitor,
                    visit_date: document.getElementById('visitDate').value || "Not Selected",
                    count: qty,
                    total: total
                })
            });
            const data = await resp.json();
            
            if (data.success && data.paid) {
                clearInterval(payPollInterval);
                document.getElementById('ticketNum').textContent = data.ticket_no === 'ALREADY_EXISTS' ? 'CONFIRMED' : data.ticket_no;
                document.getElementById('ticketVisitorText').textContent = visitor || "Valued Guest";
                document.getElementById('ticketMuseumText').textContent = museum;
                goStep(4);
            }
        } catch (err) {
            console.error("Polling Error:", err);
        }
    }, 4000); // Poll every 4 seconds to be safe
}

async function demoPaymentFlow(museum, visitor, total, btn, originalContent) {
    // Enhanced Demo Mode to show the scanner even without real keys
    document.getElementById('qrPlaceholder').style.display = 'flex';
    document.getElementById('dynamicQR').style.display = 'none';
    document.getElementById('payStatusLabel').textContent = "Generating Demo Scanner...";
    document.getElementById('qrAmount').textContent = total.toFixed(2);
    
    await new Promise(r => setTimeout(r, 800));
    
    // Use a fixed demo QR or call the backend for a real one with a mock ID
    const qrResp = await fetch('/api/generate_upi_qr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            order_id: "DEMO_" + Date.now(), 
            amount: total,
            museum: museum,
            visitor_name: visitor
        })
    });

    if (!qrResp.ok) throw new Error("Backend failed to generate demo QR");
    
    const qrData = await qrResp.json();
    
    if (qrData.success) {
        document.getElementById('qrPlaceholder').style.display = 'none';
        document.getElementById('dynamicQR').src = qrData.qr_code;
        document.getElementById('dynamicQR').style.display = 'block';
        document.getElementById('payStatusLabel').textContent = "DEMO SCANNER (Mock)";
        document.getElementById('payStatusSub').style.display = 'block';
        document.getElementById('payStatusSub').innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Simulating Verification (5s)...';
        
        // Start polling even in demo for consistency
        startPaymentPolling(null, museum, visitor, total, qrData.payment_link_id);
        
        // Finalize demo if polling isn't triggered (though it should be)
        await new Promise(r => setTimeout(r, 5000));
        
        // Note: Booking is created in startPaymentPolling for link_id success
    }
    
    btn.innerHTML = originalContent;
    btn.disabled = false;
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

function openPaymentModal(amount, museum, ticketCount, visitDate) {
    document.getElementById('bookingModal').style.display = 'flex';
    
    // Set variables from chatbot data
    qty = ticketCount || 1;
    selectedPrice = amount / qty; 
    selectedTier = "AI Assistant Booking";
    
    // Update the dropdown if a museum was provided
    if (museum) {
        const museumSelect = document.getElementById('museumSelect');
        for (let i = 0; i < museumSelect.options.length; i++) {
            if (museumSelect.options[i].text === museum) {
                museumSelect.selectedIndex = i;
                break;
            }
        }
    }

    // Update the date input if provided
    if (visitDate) {
        const dateInput = document.getElementById('visitDate');
        if (dateInput) {
            try {
                dateInput.value = visitDate; 
            } catch(e) {}
        }
    }

    // Sync UI elements
    const qtyElement = document.getElementById('qtyVal');
    if (qtyElement) qtyElement.textContent = qty.toString().padStart(2, '0');
    
    // Jump to the Checkout step (this triggers a default updateSummary)
    goStep(3);

    // CRITICAL: Override the summary date AFTER goStep(3) because updateSummary() 
    // reads from the date input which may be empty if the bot provided natural language (e.g. "Tomorrow")
    if (visitDate) {
        const sumDate = document.getElementById('sumDate');
        if (sumDate) sumDate.textContent = visitDate;
    }
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

