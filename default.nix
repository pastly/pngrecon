with import <nixpkgs> {};
#{ lib, pkgs, fetchFromGitHub }:

pkgs.python311Packages.buildPythonPackage rec {
  pname = "pngrecon";
  version = "0.2.0";
  src = fetchFromGitHub {
    owner = "pastly";
    repo = "pngrecon";
    rev = "ad112d395d7fd6b3d50a446721adaca721fdc812";
    hash = "sha256-CGfEWaq5TjBghTwAxhOG54/4i+eyDrUlxpVdc6XH45U=";
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
