
  from app.services.ami_service import AMIService
  service = AMIService()
  service._login()
  response = service.session.get(f"{service.base_url}/amiset/add")

  with open('/tmp/amiset_form.html', 'w') as f:
      f.write(response.text)
  print("Form saved to /tmp/amiset_form.html")

