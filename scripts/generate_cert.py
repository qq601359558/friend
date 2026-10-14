"""
局域网手机 / iPad 视频连麦自签名 HTTPS 证书一键生成器
解决现代移动端浏览器通过局域网 IP (如 https://192.168.1.x:8899) 访问时禁止开启摄像头与麦克风的问题。
生成后自动保存在 certs/cert.pem 与 certs/key.pem，重启 python main.py 即可自动生效。
"""
import sys
import ipaddress
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import config


def generate_self_signed_cert():
    certs_dir = config.CERTS_DIR
    certs_dir.mkdir(parents=True, exist_ok=True)
    cert_path = certs_dir / "cert.pem"
    key_path = certs_dir / "key.pem"
    lan_ip = config.get_lan_ip()

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"AI-Companion-LAN ({lan_ip})"),
        ])

        san_list = [
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]
        try:
            san_list.append(x509.IPAddress(ipaddress.IPv4Address(lan_ip)))
        except Exception:
            pass

        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
            .sign(key, hashes.SHA256())
        )

        key_path.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        print("=" * 68)
        print(f"✅ 局域网 HTTPS 证书生成成功！")
        print(f"📄 证书路径: {cert_path}")
        print(f"🔑 私钥路径: {key_path}")
        print(f"📱 现在运行 `python main.py`，即可在手机浏览器访问: https://{lan_ip}:{config.PORT}")
        print("   (首次访问时在浏览器点击“高级 -> 继续前往”即可正常开启手机摄像头与麦克风)")
        print("=" * 68)
    except ImportError:
        print("请先安装 cryptography 库: pip install cryptography")
        sys.exit(1)


if __name__ == "__main__":
    generate_self_signed_cert()
