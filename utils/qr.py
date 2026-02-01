import qrcode
import os

def generate_login_qr(login_id: str, network_url: str = None) -> str:
    if network_url:
        url = f"{network_url}/?login_id={login_id}"
    else:
        url = f"http://localhost:8501/?login_id={login_id}"

    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    if not os.path.exists("temp"):
        os.makedirs("temp")

    path = f"temp/qr_{login_id}.png"
    img.save(path)
    return path
