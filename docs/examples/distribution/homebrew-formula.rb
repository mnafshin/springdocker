class Springdocker < Formula
  desc "Spring Boot Dockerfile and benchmark workflow CLI"
  homepage "https://github.com/mnafshin/springdocker"
  url "https://github.com/mnafshin/springdocker/archive/refs/tags/v1.2.0.tar.gz"
  sha256 "REPLACE_WITH_TARBALL_SHA256"
  license "Apache-2.0"

  depends_on "python@3.12"

  def install
    system "python3", "-m", "pip", "install", ".", "--prefix=#{prefix}"
  end

  test do
    system bin/"springdocker", "--help"
  end
end
