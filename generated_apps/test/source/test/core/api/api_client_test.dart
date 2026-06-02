import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:test/core/api/api_client.dart';

void main() {
  test('ApiClient decodes list responses', () async {
    final client = ApiClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((request) async {
        expect(request.url.path, '/api/todo');
        return http.Response(
          '[{"id":"todo-1","title":"Todo","description":"One item"}]',
          200,
        );
      }),
    );

    final result = await client.getList('/api/todo');

    expect(result, hasLength(1));
    expect(result.first['title'], 'Todo');
  });

  test('ApiClient throws on failed responses', () async {
    final client = ApiClient(
      baseUrl: 'http://api.test',
      httpClient: MockClient((request) async => http.Response('bad', 500)),
    );

    expect(
      () => client.getList('/api/todo'),
      throwsA(isA<ApiException>()),
    );
  });
}
