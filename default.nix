with import <nixpkgs> {};
#{ lib, pkgs, fetchFromGitHub }:

pkgs.python311Packages.buildPythonPackage rec {
  pname = "pngrecon";
  version = "0.2.1";
  src = fetchFromGitHub {
    owner = "pastly";
    repo = "pngrecon";
    rev = "443f33c1213784a8fe755998581e01e39d6ff1a4";
    hash = "sha256-kf828v1YjTdWKRRU0/1+ujBC64d2LA81JCal2Z/FJI4=";
  };
  meta = with lib; {
    # not sure if tghese variables in the link will actually work
    homepage = "https://github.com/${src.owner}/${src.repo}";
    license = licenses.bsd3;
  };
  propagatedBuildInputs = [
    pkgs.python311Packages.cryptography
  ];
}
